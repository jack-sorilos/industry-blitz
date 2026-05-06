"""Salesforce Account data from BigQuery (raw Salesforce mirror)."""

from google.cloud import bigquery

_client = bigquery.Client(project="shopify-dw")

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
    Pull all prospect accounts for a given territory from BigQuery.
    Queries shopify-dw.raw_salesforce_banff (Salesforce mirror, 15-60 min behind live).
    Returns flat list of account dicts with nested contacts.
    """
    if territory_code is None:
        raise ValueError("territory_code is required")

    sql = """
        SELECT
            a.Id,
            a.Name,
            a.Industry,
            a.AnnualRevenue,
            a.Website,
            a.BillingCountry,
            a.Current_E_Commerce_Platform__c,
            a.Other_Current_E_Commerce_Platform__c,
            a.Merchant_Overview__c,
            a.Territory_Name__c,
            ARRAY_AGG(
                STRUCT(
                    c.FirstName,
                    c.LastName,
                    c.Title,
                    c.Phone,
                    c.MobilePhone,
                    c.Email
                )
                IGNORE NULLS
                ORDER BY c.MobilePhone DESC NULLS LAST, c.Phone DESC NULLS LAST
                LIMIT 5
            ) AS Contacts
        FROM `shopify-dw.raw_salesforce_banff.account` a
        LEFT JOIN `shopify-dw.raw_salesforce_banff.contact` c
            ON c.AccountId = a.Id
        WHERE a.Territory_Name__c = @territory
            AND (a.IsDeleted IS NULL OR a.IsDeleted = FALSE)
        GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
        ORDER BY a.Name ASC
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("territory", "STRING", territory_code),
        ]
    )

    result = _client.query(sql, job_config=job_config).result()
    all_accounts = []

    for row in result:
        account = dict(row)
        # Convert nested contacts structs to dicts
        contacts = []
        if account.get("Contacts"):
            for contact in account["Contacts"]:
                email = contact.get("Email")
                phone = contact.get("Phone") or contact.get("MobilePhone")
                if email and phone:  # Only include contacts with both email and phone
                    contacts.append({
                        "FirstName": contact.get("FirstName"),
                        "LastName": contact.get("LastName"),
                        "Title": contact.get("Title"),
                        "Phone": contact.get("Phone"),
                        "MobilePhone": contact.get("MobilePhone"),
                        "Email": contact.get("Email"),
                    })
        account["Contacts"] = contacts
        account["revenue_formatted"] = _format_revenue(account.get("AnnualRevenue"))
        all_accounts.append(account)

    return all_accounts
