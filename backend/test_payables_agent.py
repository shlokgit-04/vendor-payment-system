"""Tests for the Payables Agent layer. PayPal responses come from a
httpx.MockTransport, so no sandbox credentials are needed to run the suite."""
from datetime import date, timedelta

import os

os.environ.setdefault("DATABASE_URL", "sqlite://")

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import database
import models
import payables_agent
from paypal_client import PayPalCredentialsMissing, PayPalPayoutsClient


def make_db():
    engine = create_engine("sqlite://")
    models.Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def seed(db):
    db.add_all([
        models.Vendor(name="Alpha Prints", email="alpha@example.com", phone="1",
                      amount_due=120.50, due_date=date.today() - timedelta(days=2), payout_status=None),
        models.Vendor(name="Beta Supplies", email="beta@example.com", phone="2",
                      amount_due=75.00, due_date=date.today(), payout_status=None),
        models.Vendor(name="Gamma Corp", email="gamma@example.com", phone="3",
                      amount_due=500.00, due_date=date.today() + timedelta(days=5), payout_status=None),
        models.Vendor(name="Delta LLC", email="delta@example.com", phone="4",
                      amount_due=30.00, due_date=date.today() - timedelta(days=1), payout_status="paid"),
    ])
    db.commit()


def paypal_transport(handler):
    return httpx.MockTransport(handler)


def test_lists_only_due_unpaid_vendors():
    db = make_db()
    seed(db)
    due = payables_agent.list_due_vendors(db)
    names = [r["name"] for r in due]
    assert names == ["Alpha Prints", "Beta Supplies"]  # future due date and already-paid excluded


def test_draft_run_verifies_amounts_against_ledger():
    db = make_db()
    seed(db)
    run = payables_agent.draft_payment_run(db)
    assert run["count"] == 2
    assert run["total"] == "195.5"
    assert run["approved"] is False and run["status"] == "drafted"
    for item in run["items"]:
        v = db.query(models.Vendor).get(item["vendor_id"])
        assert item["amount"] == str(v.amount_due)  # every amount re-read from the ledger


def test_execute_refuses_unapproved_run():
    db = make_db()
    seed(db)
    run = payables_agent.draft_payment_run(db)
    with pytest.raises(PermissionError):
        payables_agent.execute_run(db, run)


def test_execute_requires_credentials():
    db = make_db()
    seed(db)
    run = payables_agent.draft_payment_run(db)
    run["approved"] = True
    client = PayPalPayoutsClient()  # no env credentials set in the test env
    with pytest.raises(PayPalCredentialsMissing):
        payables_agent.execute_run(db, run, client=client)


def test_execute_posts_batch_and_records_outcome():
    db = make_db()
    seed(db)
    run = payables_agent.draft_payment_run(db)
    run["approved"] = True

    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/v1/oauth2/token"):
            return httpx.Response(200, json={"access_token": "test-token", "expires_in": 3600})
        if path == "/v1/payments/payouts":
            calls.append(request)
            body = httpx.Request("GET", "http://x").read() and None
            return httpx.Response(201, json={"batch_header": {"payout_batch_id": "BATCH-1", "batch_status": "PENDING"}})
        if path.startswith("/v1/payments/payouts/BATCH-1"):
            return httpx.Response(200, json={
                "batch_header": {"payout_batch_id": "BATCH-1", "batch_status": "SUCCESS"},
                "items": [
                    {"payout_item": {"sender_item_id": str(i + 1)}, "transaction_status": "SUCCESS"}
                    for i in range(len(run["items"]))
                ],
            })
        return httpx.Response(404)

    client = PayPalPayoutsClient(client_id="cid", client_secret="sec", transport=paypal_transport(handler))
    payables_agent.execute_run(db, run, client=client)
    assert run["status"] == "executed" and run["payout_batch_id"] == "BATCH-1"
    assert len(calls) == 1  # exactly one payouts call

    batch = client.get_payout_batch("BATCH-1")
    outcomes = payables_agent.record_outcome(db, run, batch)
    assert all(o["payout_status"] == "paid" for o in outcomes)
    for item in run["items"]:
        v = db.query(models.Vendor).get(item["vendor_id"])
        assert v.payout_status == "paid"


def test_api_exposes_agent_tools(tmp_path):
    import main as mainmod
    mainmod.engine = create_engine(f"sqlite:///{tmp_path}/test.db")
    models.Base.metadata.create_all(mainmod.engine)
    mainmod.SessionLocal = sessionmaker(bind=mainmod.engine)
    with TestClient(mainmod.app) as c:
        r = c.post("/vendors", json={"name": "Epsilon", "email": "e@example.com", "phone": "5"})
        assert r.status_code == 200
