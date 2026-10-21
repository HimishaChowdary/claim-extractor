"""Plain-Python business rules that check the data the AI extracted.
The AI READS the document; these rules CHECK the result. No AI guessing here."""
from datetime import date

REQUIRED_FIELDS = [
    "patient_name", "policy_number", "hospital_name",
    "admission_date", "discharge_date", "diagnosis", "total_billed_amount",
]


def _parse(d):
    try:
        return date.fromisoformat(d) if d else None
    except ValueError:
        return None


def validate(claim: dict, review_threshold: float = 100000):
    """Return (status, issues). status is 'READY' or 'NEEDS REVIEW'."""
    issues = []

    # Rule 1: required fields must be present
    for field in REQUIRED_FIELDS:
        if claim.get(field) in (None, "", 0):
            issues.append(f"Missing required field: {field}")

    # Rule 2: dates must be valid and in a sensible order
    admit = _parse(claim.get("admission_date"))
    discharge = _parse(claim.get("discharge_date"))
    if claim.get("admission_date") and admit is None:
        issues.append("Admission date is not a valid date (expected YYYY-MM-DD)")
    if claim.get("discharge_date") and discharge is None:
        issues.append("Discharge date is not a valid date (expected YYYY-MM-DD)")
    if admit and discharge and discharge < admit:
        issues.append("Discharge date is BEFORE admission date")
    if admit and admit > date.today():
        issues.append("Admission date is in the future")

    # Rule 3: amount checks
    amount = claim.get("total_billed_amount")
    if isinstance(amount, (int, float)):
        if amount <= 0:
            issues.append("Billed amount must be greater than zero")
        elif amount > review_threshold:
            issues.append(f"High-value claim (above {review_threshold:,.0f}) - manual approval needed")

    # Rule 4: itemised bill should add up to the total
    items = claim.get("bill_items") or []
    if items and isinstance(amount, (int, float)):
        item_sum = sum(i.get("amount") or 0 for i in items)
        if abs(item_sum - amount) > 1:
            issues.append(f"Line items add up to {item_sum:,.2f} but total says {amount:,.2f}")

    status = "READY" if not issues else "NEEDS REVIEW"
    return status, issues
