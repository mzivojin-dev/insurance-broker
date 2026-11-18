"""/chat takes client_id only from a verified Cognito ID token. No network, no model call."""

import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from client_service import api, auth

POOL, APP = "us-east-1_TestPool", "web-app-client"
KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class FakeJWKS:   # stands in for Cognito's /.well-known/jwks.json
    def get_signing_key_from_jwt(self, token):
        return type("K", (), {"key": KEY.public_key()})()


def token(key=KEY, **over):
    claims = {"iss": auth._issuer(POOL), "aud": APP, "exp": int(time.time()) + 300,
              "token_use": "id", "custom:client_id": "C-1042", **over}
    return jwt.encode(claims, key, algorithm="RS256")


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("COGNITO_USER_POOL_ID", POOL)
    monkeypatch.setenv("COGNITO_CLIENT_ID", APP)
    monkeypatch.setattr(auth, "_jwks", lambda pool_id: FakeJWKS())
    seen = {}
    monkeypatch.setattr(api, "run", lambda case: seen.update(case) or auth_ok_transcript())
    c = TestClient(api.app)
    c.seen = seen
    return c


def auth_ok_transcript():
    from agent_core import Transcript
    return Transcript(output_text="ok", citations=["policies/C-1042/HO3-2026.pdf#Deductibles"])


def chat(c, tok, body=None):
    return c.post("/chat", json=body or {"message": "hi"},
                  headers={"Authorization": f"Bearer {tok}"})


def test_client_id_comes_from_the_token(client):
    r = chat(client, token())
    assert r.status_code == 200
    assert client.seen == {"client_id": "C-1042", "message": "hi"}


def test_client_id_in_the_body_is_ignored(client):
    r = chat(client, token(), {"message": "hi", "client_id": "C-3001"})
    assert r.status_code == 200 and client.seen["client_id"] == "C-1042"


@pytest.mark.parametrize("bad", [
    token(OTHER_KEY),                          # forged signature
    token(exp=int(time.time()) - 10),          # expired
    token(aud="some-other-app"),               # issued to another app
    token(iss="https://evil.example"),         # another issuer
    token(token_use="access"),                 # access token, not ID token
    token(**{"custom:client_id": ""}),         # user without a client
])
def test_bad_tokens_are_refused(client, bad):
    assert chat(client, bad).status_code == 401
    assert client.seen == {}


def test_no_token_is_refused(client):
    assert client.post("/chat", json={"message": "hi"}).status_code == 401


def test_refuses_everything_when_sign_in_is_not_configured(client, monkeypatch):
    monkeypatch.delenv("COGNITO_USER_POOL_ID")
    assert chat(client, token()).status_code == 503
