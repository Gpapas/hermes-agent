"""Self Agent ID registration tools.

Integrates the public Self.xyz agent registration bootstrap API exposed at:
https://app.ai.self.xyz/api/agent/bootstrap
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional

from tools.registry import registry


SELF_AGENT_BASE_URL = "https://app.ai.self.xyz"
_TIMEOUT_SECONDS = 30


def _json_response(response: Any) -> Dict[str, Any]:
    body = response.read().decode("utf-8")
    if not body:
        return {}
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return {"raw": body}
    return parsed if isinstance(parsed, dict) else {"data": parsed}


def _request(method: str, path: str, payload: Optional[Dict[str, Any]] = None, query: Optional[Dict[str, Any]] = None) -> str:
    url = SELF_AGENT_BASE_URL + path
    if query:
        qs = urllib.parse.urlencode({k: v for k, v in query.items() if v is not None})
        if qs:
            url = f"{url}?{qs}"

    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps({k: v for k, v in payload.items() if v is not None}).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT_SECONDS) as response:
            result = _json_response(response)
            result.setdefault("success", True)
            result.setdefault("status_code", getattr(response, "status", None))
            return json.dumps(result, ensure_ascii=False)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            error_body: Any = json.loads(body) if body else None
        except json.JSONDecodeError:
            error_body = body
        return json.dumps(
            {
                "success": False,
                "status_code": exc.code,
                "error": exc.reason,
                "body": error_body,
            },
            ensure_ascii=False,
        )
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False)


def check_self_agent_requirements() -> bool:
    """The Self Agent API is public and does not require local credentials."""
    return True


def start_registration(
    mode: str,
    network: str,
    human_address: Optional[str] = None,
    ed25519_pubkey: Optional[str] = None,
    ed25519_signature: Optional[str] = None,
    disclosures: Optional[Dict[str, Any]] = None,
) -> str:
    """Start a Self Agent ID registration session."""
    payload = {
        "mode": mode,
        "network": network,
        "humanAddress": human_address,
        "ed25519Pubkey": ed25519_pubkey,
        "ed25519Signature": ed25519_signature,
        "disclosures": disclosures,
    }
    return _request("POST", "/api/agent/register", payload=payload)


def poll_registration_status(token: str) -> str:
    """Poll a Self Agent ID registration session."""
    return _request("GET", "/api/agent/register/status", query={"token": token})


def export_private_key(token: str) -> str:
    """Export the server-generated agent private key after registration."""
    return _request("POST", "/api/agent/register/export", payload={"token": token})


def get_ed25519_challenge(pubkey: str, network: str, human_address: Optional[str] = None) -> str:
    """Get the Ed25519 challenge hash to sign before registration."""
    return _request(
        "POST",
        "/api/agent/register/ed25519-challenge",
        payload={"pubkey": pubkey, "network": network, "humanAddress": human_address},
    )


def regenerate_qr(token: str) -> str:
    """Regenerate QR/deep-link data for a Self Agent ID registration session."""
    return _request("GET", "/api/agent/register/qr", query={"token": token})


START_REGISTRATION_SCHEMA = {
    "name": "self_agent_start_registration",
    "description": (
        "Start a Self Agent ID registration session using the Self.xyz API. "
        "Returns a session token plus QR/deep-link data for the human to scan with the Self app. "
        "Modes 'wallet-free' and 'ed25519' do not require humanAddress; "
        "'linked', 'ed25519-linked', 'privy', and 'smartwallet' require humanAddress. "
        "For ed25519 modes, first call self_agent_ed25519_challenge, sign the challenge hash, "
        "then provide ed25519Pubkey and ed25519Signature."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "mode": {"type": "string", "enum": ["linked", "wallet-free", "ed25519", "ed25519-linked", "privy", "smartwallet"]},
            "network": {"type": "string", "enum": ["mainnet", "testnet"]},
            "humanAddress": {"type": "string", "description": "Ethereum address of the human owner when the selected mode requires it."},
            "ed25519Pubkey": {"type": "string", "description": "64-char hex Ed25519 public key, no 0x prefix."},
            "ed25519Signature": {"type": "string", "description": "128-char hex Ed25519 signature over the challenge hash, no 0x prefix."},
            "disclosures": {
                "type": "object",
                "description": "Optional disclosure requirements for the human passport verification.",
                "properties": {
                    "minimumAge": {"type": "integer", "enum": [0, 18, 21]},
                    "ofac": {"type": "boolean"},
                    "nationality": {"type": "boolean"},
                    "name": {"type": "boolean"},
                    "date_of_birth": {"type": "boolean"},
                    "gender": {"type": "boolean"},
                    "issuing_state": {"type": "boolean"},
                },
            },
        },
        "required": ["mode", "network"],
    },
}

STATUS_SCHEMA = {
    "name": "self_agent_registration_status",
    "description": "Poll a Self Agent ID registration session until the stage reaches 'registered'.",
    "parameters": {"type": "object", "properties": {"token": {"type": "string", "description": "Session token returned by self_agent_start_registration."}}, "required": ["token"]},
}

EXPORT_PRIVATE_KEY_SCHEMA = {
    "name": "self_agent_export_private_key",
    "description": (
        "Export the server-generated agent private key after successful Self Agent ID registration. "
        "Only works for modes where Self generated the keypair, such as linked and wallet-free. "
        "Handle the returned private key as a secret."
    ),
    "parameters": {"type": "object", "properties": {"token": {"type": "string", "description": "Session token returned by self_agent_start_registration."}}, "required": ["token"]},
}

ED25519_CHALLENGE_SCHEMA = {
    "name": "self_agent_ed25519_challenge",
    "description": "Get the challenge hash that must be signed with an Ed25519 private key before starting an ed25519 registration.",
    "parameters": {
        "type": "object",
        "properties": {
            "pubkey": {"type": "string", "description": "64-char hex Ed25519 public key, no 0x prefix."},
            "network": {"type": "string", "enum": ["mainnet", "testnet"]},
            "humanAddress": {"type": "string", "description": "Ethereum address of the human owner for ed25519-linked mode; omit for wallet-free ed25519."},
        },
        "required": ["pubkey", "network"],
    },
}

QR_SCHEMA = {
    "name": "self_agent_registration_qr",
    "description": "Regenerate QR code and deep-link data for an existing Self Agent ID registration session.",
    "parameters": {"type": "object", "properties": {"token": {"type": "string", "description": "Session token returned by self_agent_start_registration."}}, "required": ["token"]},
}


registry.register(
    name="self_agent_start_registration",
    toolset="self_agent",
    schema=START_REGISTRATION_SCHEMA,
    handler=lambda args, **kw: start_registration(
        mode=args.get("mode", ""),
        network=args.get("network", ""),
        human_address=args.get("humanAddress"),
        ed25519_pubkey=args.get("ed25519Pubkey"),
        ed25519_signature=args.get("ed25519Signature"),
        disclosures=args.get("disclosures"),
    ),
    check_fn=check_self_agent_requirements,
    emoji="🪪",
)

registry.register(
    name="self_agent_registration_status",
    toolset="self_agent",
    schema=STATUS_SCHEMA,
    handler=lambda args, **kw: poll_registration_status(token=args.get("token", "")),
    check_fn=check_self_agent_requirements,
    emoji="🪪",
)

registry.register(
    name="self_agent_export_private_key",
    toolset="self_agent",
    schema=EXPORT_PRIVATE_KEY_SCHEMA,
    handler=lambda args, **kw: export_private_key(token=args.get("token", "")),
    check_fn=check_self_agent_requirements,
    emoji="🪪",
)

registry.register(
    name="self_agent_ed25519_challenge",
    toolset="self_agent",
    schema=ED25519_CHALLENGE_SCHEMA,
    handler=lambda args, **kw: get_ed25519_challenge(
        pubkey=args.get("pubkey", ""),
        network=args.get("network", ""),
        human_address=args.get("humanAddress"),
    ),
    check_fn=check_self_agent_requirements,
    emoji="🪪",
)

registry.register(
    name="self_agent_registration_qr",
    toolset="self_agent",
    schema=QR_SCHEMA,
    handler=lambda args, **kw: regenerate_qr(token=args.get("token", "")),
    check_fn=check_self_agent_requirements,
    emoji="🪪",
)
