INDUSTRY_SCORES = {
    # Score 1 — Strong Fit
    "Apparel & Accessories": 1,
    "Health & Beauty (excl. Pharma)": 1,
    "Sports & Recreation (excl. Firearms)": 1,
    "Home Decor": 1,
    "Furniture": 1,
    "Gifts & Collectibles": 1,
    "Animals & Pet Supplies": 1,
    "Food & Beverage (excl. Alcohol)": 1,
    "Toys & Games": 1,
    # Score 2 — Good Fit
    "Electronics & Gadgets": 2,
    "Stationery & Office Supplies": 2,
    "Vehicles & Parts": 2,
    "Art & Photography": 2,
    "Entertainment": 2,
    # Score 3 — Weak Fit
    "Construction & Industrial": 3,
    "Services": 3,
    "Media & Communication": 3,
    "Banking, Finance, Insurance": 3,
    "Travel & Tourism": 3,
    "Other": 3,
}
INDUSTRY_SCORE_DEFAULT = 3

PLATFORM_SCORES = {
    # Score 1 — Critical Pain
    "Adobe Commerce (Magento)": 1,
    "Custom Build": 1,
    "HCL Commerce": 1,
    "SAP Commerce Cloud (Hybris)": 1,
    "Oracle (Commerce/Cloud/SuiteCommerce/ATG)": 1,
    "Spryker": 1,
    # Score 2 — High Pain
    "WooCommerce": 2,
    "Salesforce Commerce Cloud": 2,
    "Prestashop": 2,
    "Shopware": 2,
    "VTEX": 2,
    "Scayle": 2,
    # Score 3 — Medium Pain
    "BigCommerce": 3,
    "OpenCart": 3,
    "Visualsoft": 3,
    "Wix": 3,
    "Squarespace": 3,
    "Drupal": 3,
    "commercetools": 3,
    "Centra": 3,
    "Odoo": 3,
    "osCommerce": 3,
    "Lightspeed": 3,
    "Novomind": 3,
    "SpreeCommerce": 3,
    "Yahoo Commerce": 3,
    "Other": 3,
    # Score 4 — Low Urgency
    "Shopify Plan Advanced/Basic": 4,
    "None": 4,
}
PLATFORM_SCORE_DEFAULT = 4

PRIORITY_MATRIX = {
    (1, 1): "HOT",
    (1, 2): "HOT",
    (1, 3): "WARM",
    (1, 4): "WARM",
    (2, 1): "HOT",
    (2, 2): "WARM",
    (2, 3): "WARM",
    (2, 4): "LOW",
    (3, 1): "WARM",
    (3, 2): "LOW",
    (3, 3): "LOW",
    (3, 4): "LOW",
}

def score_account(account: dict) -> dict:
    """Add scoring fields to account dict. Returns the modified dict."""
    industry = account.get("Industry") or ""
    platform = account.get("Current_E_Commerce_Platform__c") or ""

    ind_score = INDUSTRY_SCORES.get(industry, INDUSTRY_SCORE_DEFAULT)
    plat_score = PLATFORM_SCORES.get(platform, PLATFORM_SCORE_DEFAULT)
    combined = ind_score * plat_score

    tier = PRIORITY_MATRIX.get((ind_score, plat_score), "LOW")

    account["industry_score"] = ind_score
    account["platform_score"] = plat_score
    account["priority_score"] = combined
    account["priority_tier"] = tier
    account["priority_color"] = {"HOT": "red", "WARM": "amber", "LOW": "grey"}.get(tier, "grey")
    account["industry_label"] = {1: "Strong Fit", 2: "Good Fit", 3: "Weak Fit"}.get(ind_score, "Unknown")
    account["platform_label"] = {
        1: "Critical Pain",
        2: "High Pain",
        3: "Medium Pain",
        4: "Low Urgency"
    }.get(plat_score, "Unknown")

    return account

def sort_accounts(accounts: list) -> list:
    """
    Sort by: priority_tier (HOT, WARM, LOW), then priority_score ASC, then AnnualRevenue DESC.
    Lower priority_score = higher priority within each tier.
    """
    tier_order = {"HOT": 0, "WARM": 1, "LOW": 2}
    return sorted(accounts,
                  key=lambda a: (
                      tier_order.get(a.get("priority_tier", "LOW"), 3),
                      a.get("priority_score", 999),
                      -(a.get("AnnualRevenue") or 0)
                  ))
