"""The Payables Agent: an agent layer over the vendor ledger.

The agent prepares; the human holds the trigger. Every amount in a run is
re-read from the ledger and cross-checked before it is ever offered for
execution, and execute_run refuses to send a run that has not been approved.
"""
from datetime import date

from paypal_client import PayPalCredentialsMissing, PayPalPayoutsClient


def list_due_vendors(db, today=None):
    """Vendors with an outstanding amount whose due date has arrived."""
    today = today or date.today()
    due = []
    for v in db.query(__import__("models").Vendor).all():
        if v.amount_due and v.amount_due > 0 and v.due_date and v.due_date <= today and v.payout_status != "paid":
            due.append({
                "vendor_id": v.id,
                "name": v.name,
                "receiver_email": v.email,
                "amount": str(v.amount_due),
                "due_date": v.due_date.isoformat(),
                "payout_status": v.payout_status or "pending",
            })
    due.sort(key=lambda r: (r["due_date"], r["name"]))
    return due


def draft_payment_run(db, today=None):
    """Draft a payout run from the ledger. Amounts are re-read from the DB rows
    here, so what the operator reviews is exactly what the ledger says."""
    today = today or date.today()
    items = []
    for row in list_due_vendors(db, today=today):
        v = db.query(__import__("models").Vendor).get(row["vendor_id"])
        ledger_amount = str(v.amount_due)
        if ledger_amount != row["amount"]:
            raise ValueError(f"ledger mismatch for vendor {v.id}: {ledger_amount} != {row['amount']}")
        items.append({
            "vendor_id": v.id,
            "name": v.name,
            "receiver_email": v.email,
            "amount": ledger_amount,
            "currency": "USD",
        })
    run = {
        "run_id": f"PR-{date.today().isoformat()}",
        "status": "drafted",
        "approved": False,
        "items": items,
        "total": str(sum(float(i["amount"]) for i in items)),
        "count": len(items),
    }
    return run


def execute_run(db, run, client=None, approver=None):
    """Execute an approved run through the PayPal payouts API (sandbox).
    Refuses any run that has not been approved by a human operator."""
    if run["status"] != "drafted" or not run.get("approved"):
        raise PermissionError("run is not approved: the human holds the trigger")
    if not run["items"]:
        raise ValueError("nothing to execute: the run is empty")
    client = client or PayPalPayoutsClient()
    response = client.create_payout_batch(run["items"], note=run["run_id"])
    batch_id = response.get("batch_header", {}).get("payout_batch_id")
    run["status"] = "executed"
    run["payout_batch_id"] = batch_id
    run["approver"] = approver
    return response


def record_outcome(db, run, batch_result):
    """Reconcile ledger payout_status from a payouts batch response."""
    items = run["items"]
    batch_items = {}
    for it in batch_result.get("items", []):
        sender_item_id = it.get("payout_item", {}).get("sender_item_id") or it.get("sender_item_id")
        if sender_item_id is not None:
            batch_items[str(sender_item_id)] = it.get("transaction_status", it.get("status", "UNKNOWN"))
    updated = []
    for item in items:
        v = db.query(__import__("models").Vendor).get(item["vendor_id"])
        status = batch_items.get(str(item["vendor_id"]), "PENDING")
        v.payout_status = "paid" if status == "SUCCESS" else status.lower()
        updated.append({"vendor_id": v.id, "payout_status": v.payout_status})
    db.commit()
    return updated
