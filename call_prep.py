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
1. "opening" — conversational script for when they answer. Include: [First name], [Your name], platform name ({platform}), platform-specific pain point. Start with "Hi [First name]..."
2. "voicemail" — 22 seconds max. Value-focused. Platform pain point. Start with "Hi [First name]..."
3. ONE-LINER bullets only: 3 talking points, 3 discovery questions, 3 objections with responses.

Return ONLY this JSON (no other text, no markdown, no escapes):
{{"opening": "Hi [First name], [Your name]...", "voicemail": "Hi [First name], [Your name]...", "talking_points": [{{"headline": "point 1", "detail": ""}}], "discovery_questions": [{{"question": "question 1", "why": ""}}], "objection_handlers": [{{"objection": "objection 1", "response": "response 1"}}]}}"""

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

    # Strip markdown code fences and extract JSON
    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:].lstrip()

    # Extract JSON object from response (find { to })
    json_start = raw.find('{')
    json_end = raw.rfind('}')
    if json_start >= 0 and json_end > json_start:
        raw = raw[json_start:json_end+1]

    raw = raw.strip()

    try:
        prep = json.loads(raw)
    except json.JSONDecodeError as e:
        # Fallback: return generic prep
        prep = {
            "opening": "Hi [First name], [Your name] from Shopify — I hope now's not a bad moment? I reached out earlier about your platform. How long have you been on it and how are you finding it?",
            "voicemail": "Hi [First name], [Your name] from Shopify. I emailed about platform maintenance and scaling. Just some insights that tend to surprise people. My number is [number], or reply to the email. Thanks.",
            "talking_points": [
                {"headline": "Industry-specific growth challenges", "detail": ""},
                {"headline": "Platform capability gaps", "detail": ""},
                {"headline": "Plus features that unlock revenue", "detail": ""}
            ],
            "discovery_questions": [
                {"question": "What's your biggest growth bottleneck right now?", "why": "Understand pain points"},
                {"question": "How are you handling [platform]-specific limitations?", "why": "Identify platform friction"},
                {"question": "What would 10x growth require?", "why": "Assess Plus fit"}
            ],
            "objection_handlers": [
                {"objection": "Timing isn't right", "response": "When would be ideal to reconnect?"},
                {"objection": "We're happy with our platform", "response": "What would make a change worth considering?"},
                {"objection": "We're not interested in migration", "response": "What if you didn't have to migrate everything at once?"}
            ],
            "error": False
        }

    _prep_cache[account_id] = prep
    return prep
