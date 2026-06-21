import json

from tools import self_agent_tool
from tools.registry import registry
from toolsets import resolve_toolset


class FakeResponse:
    status = 200

    def __init__(self, body):
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_self_agent_toolset_resolves_registered_tools():
    tools = set(resolve_toolset("self_agent"))

    assert {
        "self_agent_start_registration",
        "self_agent_registration_status",
        "self_agent_export_private_key",
        "self_agent_ed25519_challenge",
        "self_agent_registration_qr",
    }.issubset(tools)


def test_start_registration_posts_expected_payload(monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout):
        captured["url"] = req.full_url
        captured["method"] = req.get_method()
        captured["body"] = json.loads(req.data.decode("utf-8"))
        captured["timeout"] = timeout
        return FakeResponse(b'{"token":"session-token","stage":"qr"}')

    monkeypatch.setattr(self_agent_tool.urllib.request, "urlopen", fake_urlopen)

    result = json.loads(
        self_agent_tool.start_registration(
            mode="wallet-free",
            network="testnet",
            disclosures={"minimumAge": 18, "ofac": True},
        )
    )

    assert captured["url"] == "https://app.ai.self.xyz/api/agent/register"
    assert captured["method"] == "POST"
    assert captured["body"] == {
        "mode": "wallet-free",
        "network": "testnet",
        "disclosures": {"minimumAge": 18, "ofac": True},
    }
    assert captured["timeout"] == 30
    assert result["success"] is True
    assert result["token"] == "session-token"


def test_status_uses_query_token(monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout):
        captured["url"] = req.full_url
        captured["method"] = req.get_method()
        return FakeResponse(b'{"stage":"registered"}')

    monkeypatch.setattr(self_agent_tool.urllib.request, "urlopen", fake_urlopen)

    result = json.loads(self_agent_tool.poll_registration_status("abc 123"))

    assert captured["method"] == "GET"
    assert captured["url"] == "https://app.ai.self.xyz/api/agent/register/status?token=abc+123"
    assert result["success"] is True
    assert result["stage"] == "registered"


def test_registered_tool_handler_invokes_api(monkeypatch):
    def fake_start_registration(**kwargs):
        return json.dumps(kwargs)

    monkeypatch.setattr(self_agent_tool, "start_registration", fake_start_registration)
    entry = registry.get_entry("self_agent_start_registration")

    assert entry is not None
    result = json.loads(entry.handler({"mode": "wallet-free", "network": "testnet"}))

    assert result["mode"] == "wallet-free"
    assert result["network"] == "testnet"
