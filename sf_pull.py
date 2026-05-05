import subprocess
import json
import shutil
import os

def _run_soql(query: str, org_alias: str) -> dict:
    """Execute SOQL query via SF CLI and return parsed JSON result."""
    sf_bin = shutil.which("sf") or "/Users/jacksorilos/.local/share/pnpm/sf"
    cmd = [sf_bin, "data", "query",
           "--query", query,
           "--target-org", org_alias,
           "--json"]

    env = os.environ.copy()
    if "/Users/jacksorilos/.local/share/pnpm" not in env.get("PATH", ""):
        env["PATH"] = env.get("PATH", "") + ":/Users/jacksorilos/.local/share/pnpm"

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=env)
    if result.returncode != 0:
        raise RuntimeError(f"SF CLI error: {result.stderr[:500]}")

    parsed = json.loads(result.stdout)
    return parsed

def _format_revenue(val):
    """Format revenue in millions, billions, or thousands."""
    if not val:
        return "N/A"
    if val >= 1_000_000_000:
        return f"${val/1e9:.1f}B"
    if val >= 1_000_000:
        return f"${val/1e6:.0f}M"
    return f"${val/1000:.0f}K"

def pull_accounts(org_alias: str = "BanffProd", territory_code: str = None) -> list:
    """
    Pull all prospect accounts for a given territory.
    Paginates in 2000-record chunks due to SOQL limit.
    Returns flat list of account dicts with nested contacts.
    """
    if territory_code is None:
        raise ValueError("territory_code is required")

    all_accounts = []
    soql_base = """
SELECT
    Id,
    Name,
    Industry,
    AnnualRevenue,
    Website,
    BillingCountry,
    Current_E_Commerce_Platform__c,
    Other_Current_E_Commerce_Platform__c,
    (
        SELECT
            Id,
            FirstName,
            LastName,
            Title,
            MobilePhone,
            Phone,
            Email
        FROM Contacts
        ORDER BY MobilePhone DESC NULLS LAST, Phone DESC NULLS LAST
        LIMIT 5
    )
FROM Account
WHERE Territory_Name__c = '{territory_code}'
ORDER BY Name ASC
LIMIT 2000
OFFSET {offset}
    """

    offset = 0
    while True:
        query = soql_base.format(territory_code=territory_code, offset=offset)
        response = _run_soql(query, org_alias)
        records = response.get("result", {}).get("records", [])

        for record in records:
            # Extract contacts (handle None case from Salesforce)
            contacts_obj = record.get("Contacts")
            contacts = contacts_obj.get("records", []) if contacts_obj else []
            record["Contacts"] = contacts
            record["revenue_formatted"] = _format_revenue(record.get("AnnualRevenue"))
            all_accounts.append(record)

        if len(records) < 2000:
            break

        offset += 2000

    return all_accounts
