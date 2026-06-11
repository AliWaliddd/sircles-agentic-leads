from __future__ import annotations

from typer.testing import CliRunner

from sircles_agents.main import app


runner = CliRunner()


def test_cli_lists_fixture_leads() -> None:
    result = runner.invoke(app, ["list-leads"])

    assert result.exit_code == 0, result.output
    assert "Available Mock Leads" in result.output
    assert "Maya Chen" in result.output
    assert "Omar Nasser" in result.output
    assert "GlowCart" in result.output
    assert "BrightBridge Growth" in result.output


def test_cli_runs_single_lead_and_writes_trace(tmp_path) -> None:
    result = runner.invoke(
        app,
        [
            "run",
            "lead_saas_pursue",
            "--trace-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "lead_saas_pursue" in result.output
    assert "pursue" in result.output

    trace_path = tmp_path / "lead_saas_pursue_trace.json"
    assert trace_path.exists()