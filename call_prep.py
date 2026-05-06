import os
import json
import re
import requests

_prep_cache = {}

SYSTEM_PROMPT = """Generate brief call prep with one-liner bullet points only. No paragraphs. Return ONLY valid JSON, no other text. Ensure all strings are properly escaped and closed."""

def _call_proxy_api(prompt: str) -> str:
    """Call the Shopify AI Proxy with IAP authentication."""
    proxy_token = os.environ.get("SHOPIFY_AI_PROXY_TOKEN")
    if not proxy_token:
        raise ValueError("SHOPIFY_AI_PROXY_TOKEN not set in environment")

    url = "https://proxy.shopify.ai/apis/anthropic/v1/messages"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {proxy_token}"
    }

    payload = {
        "model": "claude-sonnet-4-6",
        "max_tokens": 400,
        "system": SYSTEM_PROMPT,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    response = requests.post(url, json=payload, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()["content"][0]["text"]

def _build_prompt(account: dict) -> str:
    """Build the user prompt for call prep generation."""
    name = account.get("Name", "Unknown")
    industry = account.get("Industry", "Unknown")
    platform = account.get("Current_E_Commerce_Platform__c", "Unknown")
    if platform == "Other":
        other = account.get("Other_Current_E_Commerce_Platform__c", "")
        if other:
            platform = f"Other ({other})"
    revenue = account.get("revenue_formatted", "N/A")
    country = account.get("BillingCountry", "Unknown")
    industry_score = account.get("industry_score", 0)
    industry_label = account.get("industry_label", "Unknown")
    platform_score = account.get("platform_score", 0)
    platform_label = account.get("platform_label", "Unknown")
    priority_score = account.get("priority_score", 0)
    priority_tier = account.get("priority_tier", "Unknown")

    # Merchant context from Salesforce (strip HTML tags and escape newlines)
    merchant_overview = account.get("Merchant_Overview__c") or ""
    merchant_overview = re.sub(r'<[^>]+>', '', merchant_overview).strip()
    merchant_overview = merchant_overview.replace('\n', ' ').replace('\r', ' ')[:500]
    overview_section = f"\nMERCHANT CONTEXT: {merchant_overview}\nUse this context to personalise the talking points." if merchant_overview else ""

    prompt = f"""Quick prep for {name} ({industry} on {platform}, {revenue} GMV, {country}).

Generate:
1. A brief opening line (Jason Bay style — direct, value-focused, no fluff). Max 1-2 sentences. Example: "Hi this is Jack from Shopify. We work with leading {industry} brands moving to Plus to handle 10x growth."
2. ONE-LINER bullets only:
- 3 talking points (headline only)
- 3 discovery questions (one line each)
- 3 objections (objection + one-line response)

Return JSON:
{{"intro": "opening line here", "talking_points": [{{"headline": "one-liner", "detail": ""}}], "discovery_questions": [{{"question": "one-liner", "why": ""}}], "objection_handlers": [{{"objection": "one-liner", "response": "one-liner"}}]}}"""

    return prompt

def generate_call_prep(account: dict) -> dict:
    """Generate AI call prep for an account. Results are cached per-session."""
    account_id = account["Id"]
    if account_id in _prep_cache:
        return _prep_cache[account_id]

    prompt = _build_prompt(account)

    try:
        raw = _call_proxy_api(prompt).strip()
    except Exception as e:
        return {
            "talking_points": [{"headline": "API Error", "detail": str(e)[:200]}],
            "discovery_questions": [],
            "objection_handlers": [],
            "error": True
        }

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        prep = json.loads(raw)
    except json.JSONDecodeError as e:
        try:
            raw_fixed = raw + ']}' if not raw.endswith('}') else raw
            prep = json.loads(raw_fixed)
        except:
            prep = {
                "talking_points": [{"headline": "Generation error", "detail": str(e)[:200]}],
                "discovery_questions": [],
                "objection_handlers": [],
                "error": True
            }

    _prep_cache[account_id] = prep
    return prep
