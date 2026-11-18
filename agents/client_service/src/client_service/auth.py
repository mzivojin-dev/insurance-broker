"""Who is asking: the client_id comes from a verified Cognito ID token, never from the request body.

Needs COGNITO_USER_POOL_ID (e.g. us-east-1_AbC123) and COGNITO_CLIENT_ID (the web app client).
Without them /chat refuses every request rather than guessing a client.
"""

from __future__ import annotations

import os
from functools import lru_cache

import jwt
from fastapi import Header, HTTPException

# Set by an admin when the user is created; the web app client can read it but not write it.
CLIENT_CLAIM = "custom:client_id"


def _issuer(pool_id: str) -> str:
    region = pool_id.split("_", 1)[0]          # pool IDs look like us-east-1_AbC123
    return f"https://cognito-idp.{region}.amazonaws.com/{pool_id}"


@lru_cache
def _jwks(pool_id: str) -> jwt.PyJWKClient:   # one per process; it caches Cognito's keys
    return jwt.PyJWKClient(f"{_issuer(pool_id)}/.well-known/jwks.json")


def client_id_from_token(token: str, pool_id: str, app_client_id: str,
                         jwks: jwt.PyJWKClient | None = None) -> str:
    """Verify signature, issuer, audience, expiry and token_use; return the client_id claim."""
    key = (jwks or _jwks(pool_id)).get_signing_key_from_jwt(token).key
    claims = jwt.decode(token, key, algorithms=["RS256"], audience=app_client_id,
                        issuer=_issuer(pool_id), options={"require": ["exp", "iss", "aud"]})
    if claims.get("token_use") != "id":
        raise jwt.InvalidTokenError("not an ID token")
    if not claims.get(CLIENT_CLAIM):
        raise jwt.InvalidTokenError(f"no {CLIENT_CLAIM} on this user")
    return claims[CLIENT_CLAIM]


def signed_in_client(authorization: str = Header(default="")) -> str:
    """FastAPI dependency: the client_id of the signed-in user, or 401/503."""
    pool_id = os.environ.get("COGNITO_USER_POOL_ID")
    app_client_id = os.environ.get("COGNITO_CLIENT_ID")
    if not (pool_id and app_client_id):
        raise HTTPException(503, "sign-in is not configured on this service")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(401, "sign in first")
    try:
        return client_id_from_token(token, pool_id, app_client_id)
    except jwt.PyJWTError as exc:
        raise HTTPException(401, f"invalid token: {exc}") from exc
