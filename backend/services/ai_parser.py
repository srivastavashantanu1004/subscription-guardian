import anthropic
import json
import re
from config import supabase, ANTHROPIC_API_KEY

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

def parse_subscription(text: str, user_id: str):

    prompt = f"""
    Analyze this email/receipt and extract subscription information.
    Return ONLY a JSON object with NO extra text, NO markdown, NO backticks.
    Just the raw JSON:
    {{
        "vendor": "company name",
        "amount": 9.99,
        "billing_cycle": "monthly",
        "renewal_date": "2026-10-15",
        "trial_expiry_date": null,
        "hidden_clauses": [
            {{
                "clause_text": "exact text from document",
                "clause_type": "cancellation_fee",
                "severity": "high",
                "ai_summary": "plain english explanation"
            }}
        ]
    }}

    clause_type must be one of: cancellation_fee, auto_renew, price_hike, notice_period
    severity must be one of: high, medium, low
    billing_cycle must be one of: monthly, annual, weekly, one-time
    dates must be in YYYY-MM-DD format or null

    Document to analyze:
    {text}
    """

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )

    response_text = message.content[0].text
    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
    if json_match:
        result = json.loads(json_match.group())
    else:
        result = json.loads(response_text)

    sub = supabase.table("subscriptions").insert({
        "user_id": user_id,
        "vendor": result["vendor"],
        "amount": result["amount"],
        "billing_cycle": result["billing_cycle"],
        "renewal_date": result["renewal_date"],
        "trial_expiry_date": result["trial_expiry_date"],
        "raw_source": text,
        "source_type": "email",
        "status": "active"
    }).execute()

    sub_id = sub.data[0]["id"]

    for clause in result.get("hidden_clauses", []):
        supabase.table("hidden_clauses").insert({
            "subscription_id": sub_id,
            "clause_text": clause["clause_text"],
            "clause_type": clause["clause_type"],
            "severity": clause["severity"],
            "ai_summary": clause["ai_summary"]
        }).execute()

    return {"subscription_id": sub_id, "parsed": result}
