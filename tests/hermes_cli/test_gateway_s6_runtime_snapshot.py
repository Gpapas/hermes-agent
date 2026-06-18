"""Regression tests for s6-backed gateway runtime status in containers."""

from pathlib import Path

import hermes_cli.gateway as gateway_mod


class _FakeS6ServiceManager:
    def _service_dir(self, profile: str) -> Path:
        assert profile == "default"
        return Path("/run/service/gateway-default")

    def is_running(self, service_name: str) -> bool:
        assert service_name == "gateway-default"
        return True


def test_container_s6_snapshot_uses_service_state_when_pid_scan_empty(monkeypatch):
    """An in-gateway status call may exclude the gateway ancestor PID.

    In Docker/s6, the s6 service slot is the authoritative liveness source and
    should make `hermes gateway status` report running even when the fallback
    PID scan returns no non-ancestor gateway processes.
    """

    monkeypatch.setattr(gateway_mod, "is_linux", lambda: True)
    monkeypatch.setattr("hermes_constants.is_container", lambda: True)
    monkeypatch.setattr(gateway_mod, "_scan_gateway_pids", lambda *a, **k: [])
    monkeypatch.setattr("hermes_cli.profiles.get_active_profile_name", lambda: "default")
    monkeypatch.setattr("hermes_cli.service_manager.detect_service_manager", lambda: "s6")
    monkeypatch.setattr("hermes_cli.service_manager.S6ServiceManager", _FakeS6ServiceManager)
    monkeypatch.setattr(Path, "is_dir", lambda self: str(self) == "/run/service/gateway-default")

    snapshot = gateway_mod.get_gateway_runtime_snapshot()

    assert snapshot.manager == "s6 (container supervisor)"
    assert snapshot.service_installed is True
    assert snapshot.service_running is True
    assert snapshot.service_scope == "gateway-default"
    assert snapshot.gateway_pids == ()
