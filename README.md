# Industry Blitz

Territory-based prospecting tool for Shopify AE call prep. Pulls your Salesforce accounts, generates AI talking points + discovery questions, exports emails to CSV.

## Setup (10 min, one-time)

### Prerequisites
- Python 3.12+
- Google Cloud credentials (BigQuery read access to `shopify-dw.raw_salesforce_banff`)
- Shopify Anthropic API token (ask Jack)

### Install

```bash
git clone https://github.com/Shopify/industry-blitz.git
cd industry-blitz

# Create .env file with your Anthropic token
cat > .env <<EOF
SHOPIFY_AI_PROXY_TOKEN=<your-token-from-jack>
EOF

# First run (creates venv, installs deps, opens browser)
bash run.sh
```

Browser opens to http://localhost:5000 → enter your **territory code** (e.g., `EMEA_SMB_All_All_A_D2C_01`)

### GCP Credentials Setup
The tool queries BigQuery directly. Authenticate with:
```bash
gcloud auth application-default login
```
Then log in with your Shopify account. You need read access to `shopify-dw.raw_salesforce_banff` tables.

## Usage

**Login:** Enter your Salesforce Territory_Name__c code

**Filter accounts:** Industry, Country, Platform, Priority tier

**Generate AI prep:** Click "Generate with AI" on any card → talking points + discovery questions + objection handlers

**Export emails:** Click "Download CSV" to export filtered accounts' contact emails

**Refresh data:** Click "Refresh Data" to re-pull from Salesforce (runs in background)

## Territory Codes

Find yours in Salesforce:
1. Go to Accounts
2. Pick any account in your book
3. Look at the "Territory Name" field
4. Copy the exact value (e.g., `EMEA_SMB_All_All_A_D2C_01`)

## Issues?

- `Can't find sf CLI` → reinstall Salesforce CLI
- `Territory code not found` → double-check the exact spelling in Salesforce
- `AI prep fails` → check SHOPIFY_AI_PROXY_TOKEN in .env

Ask Jack for help.
