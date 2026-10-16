"""PayPal payouts API client (sandbox-first).

Credentials come from the environment:
  PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET  (PayPal developer account, sandbox app)
  PAYPAL_API_BASE (optional, defaults to the sandbox host; never a live host in this repo)
"""
import os
import time
import httpx

SANDBOX_BASE = "https://api-m.sandbox.paypal.com"


class PayPalCredentialsMissing(Exception):
    """Raised when PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET are not configured."""


class PayPalPayoutsClient:
    """Thin client for the PayPal payouts API. Sandbox by default, always."""

    def __init__(self, client_id=None, client_secret=None, base_url=None, transport=None):
        self.client_id = client_id or os.environ.get("PAYPAL_CLIENT_ID")
        self.client_secret = client_secret or os.environ.get("PAYPAL_CLIENT_SECRET")
        self.base_url = (base_url or os.environ.get("PAYPAL_API_BASE") or SANDBOX_BASE).rstrip("/")
        self._token = None
        self._token_expiry = 0.0
        self._http = httpx.Client(transport=transport, timeout=30.0)

    @property
    def configured(self):
        return bool(self.client_id and self.client_secret)

    def _auth(self):
        if not self.configured:
            raise PayPalCredentialsMissing(
                "Set PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET (PayPal developer sandbox app) to execute runs."
            )
        if self._token is None or time.time() >= self._token_expiry:
            resp = self._http.post(
                f"{self.base_url}/v1/oauth2/token",
                data={"grant_type": "client_credentials"},
                auth=(self.client_id, self.client_secret),
            )
            resp.raise_for_status()
            body = resp.json()
            self._token = body["access_token"]
            self._token_expiry = time.time() + int(body.get("expires_in", 3600)) - 60
        return self._token

    def _headers(self):
        return {"Authorization": f"Bearer {self._auth()}", "Content-Type": "application/json"}

    def create_payout_batch(self, items, note="Payables Agent run"):
        """items: [{"receiver_email": ..., "amount": "12.50", "currency": "USD", ...}]
        Returns the raw payouts response (batch header + links)."""
        body = {
            "sender_batch_header": {
                "sender_note": note,
                "recipient_type": "EMAIL",
                "email_subject": "You have a payment",
            },
            "items": [
                {
                    "amount": {"value": str(it["amount"]), "currency": it.get("currency", "USD")},
                    "receiver": it["receiver_email"],
                    "note": it.get("note", note),
                    "sender_item_id": str(it.get("vendor_id", "")),
                }
                for it in items
            ],
        }
        resp = self._http.post(f"{self.base_url}/v1/payments/payouts", headers=self._headers(), json=body)
        resp.raise_for_status()
        return resp.json()

    def get_payout_batch(self, batch_id):
        resp = self._http.get(f"{self.base_url}/v1/payments/payouts/{batch_id}", headers=self._headers())
        resp.raise_for_status()
        return resp.json()
