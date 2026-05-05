from flask import Flask, render_template, request, jsonify, send_file, Response, session, redirect
import os
import json
import csv
import io
import threading
from dotenv import load_dotenv
from sf_pull_bigquery import pull_accounts
from scoring import score_account, sort_accounts
from call_prep import generate_call_prep

load_dotenv()

import os as _os
_os.environ.setdefault("HOME", "/tmp")
_os.environ.setdefault("SF_USE_GENERIC_UNIX_KEYCHAIN", "true")

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.environ.get("SECRET_KEY", "dev-key-change-in-production"))
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    JSON_SORT_KEYS=False,
)

_cache = {
    "accounts": [],
    "last_pulled": None,
    "is_loading": False,
}

_current_territory = None

def _do_refresh(territory_code):
    """Pull and score all accounts in background."""
    _cache["is_loading"] = True
    try:
        accounts = pull_accounts(
            org_alias=os.environ.get("SF_ORG_ALIAS", "BanffProd"),
            territory_code=territory_code
        )
        scored = [score_account(a) for a in accounts]
        sorted_accs = sort_accounts(scored)
        _cache["accounts"] = sorted_accs
        _cache["last_pulled"] = "Just now"
    except Exception as e:
        _cache["accounts"] = []
        _cache["last_pulled"] = f"Error: {str(e)[:100]}"
    finally:
        _cache["is_loading"] = False

@app.route("/login", methods=["GET", "POST"])
def login():
    """Login with territory code."""
    if request.method == "POST":
        territory_code = request.form.get("territory_code", "").strip()
        if territory_code:
            session["territory_code"] = territory_code
            # Trigger data pull
            t = threading.Thread(target=_do_refresh, args=(territory_code,), daemon=True)
            t.start()
            return jsonify({"status": "pulling"}), 202
        return jsonify({"error": "Territory code required"}), 400

    return render_template("login.html")

@app.route("/")
def index():
    """Render the main card UI."""
    if "territory_code" not in session:
        return redirect("/login")

    accounts = _cache.get("accounts", [])

    # Extract unique values for filter dropdowns
    industries = sorted(set(a.get("Industry") for a in accounts if a.get("Industry")))
    countries = sorted(set(a.get("BillingCountry") for a in accounts if a.get("BillingCountry")))
    platforms = sorted(set(
        a.get("Current_E_Commerce_Platform__c") for a in accounts
        if a.get("Current_E_Commerce_Platform__c")
    ))

    return render_template(
        "index.html",
        accounts=accounts,
        industries=industries,
        countries=countries,
        platforms=platforms
    )

@app.route("/status")
def status():
    """Check if Salesforce data pull is complete."""
    return jsonify({
        "loading": _cache["is_loading"],
        "count": len(_cache["accounts"]),
        "last_pulled": _cache["last_pulled"]
    })

@app.route("/refresh", methods=["POST"])
def refresh():
    """Trigger Salesforce data pull in background."""
    if "territory_code" not in session:
        return jsonify({"error": "Not logged in"}), 401
    if not _cache["is_loading"]:
        t = threading.Thread(target=_do_refresh, args=(session["territory_code"],), daemon=True)
        t.start()
    return jsonify({"status": "pulling"}), 202

@app.route("/generate_prep", methods=["POST"])
def generate_prep():
    """Generate AI call prep for a specific account."""
    data = request.json
    account_id = data.get("account_id")

    # Find account in cache
    account = next((a for a in _cache["accounts"] if a["Id"] == account_id), None)
    if not account:
        return jsonify({"error": "Account not found"}), 404

    try:
        prep = generate_call_prep(account)
        return jsonify(prep)
    except Exception as e:
        import traceback
        print(f"ERROR generating prep: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": str(e), "type": type(e).__name__}), 500

@app.route("/export.csv")
def export_csv():
    """Export filtered accounts' email addresses to CSV."""
    accounts = _cache.get("accounts", [])

    # Apply filters from query params
    tier = request.args.get("tier", "").strip()
    industries = request.args.getlist("industry")
    countries = request.args.getlist("country")
    platforms = request.args.getlist("platform")

    if tier:
        accounts = [a for a in accounts if a.get("priority_tier") == tier]
    if industries:
        accounts = [a for a in accounts if a.get("Industry") in industries]
    if countries:
        accounts = [a for a in accounts if a.get("BillingCountry") in countries]
    if platforms:
        accounts = [a for a in accounts if a.get("Current_E_Commerce_Platform__c") in platforms]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Email"])

    for account in accounts:
        contacts = account.get("Contacts", [])
        primary = contacts[0] if contacts else {}
        email = primary.get("Email", "")
        if email:
            writer.writerow([email])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=industry-blitz-export.csv"}
    )

@app.route("/health")
def health():
    """Health check endpoint."""
    return jsonify({"ok": True})

if __name__ == "__main__":
    # Auto-pull on startup if cache is empty
    if not _cache["accounts"]:
        t = threading.Thread(target=_do_refresh, daemon=True)
        t.start()

    app.run(debug=False, port=5000, host="127.0.0.1")
