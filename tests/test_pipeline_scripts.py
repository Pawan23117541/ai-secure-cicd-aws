"""Tests for the security gate and the AI log analyzer (no AWS needed)."""

import json

import ai_log_analyzer
import security_gate


def test_gate_blocks_high_bandit_and_fixable_critical_trivy(tmp_path):
    bandit = tmp_path / "bandit.json"
    bandit.write_text(
        json.dumps(
            {
                "results": [
                    {
                        "test_id": "B602",
                        "issue_severity": "HIGH",
                        "filename": "app/x.py",
                        "line_number": 3,
                        "issue_text": "shell=True",
                    },
                    {
                        "test_id": "B101",
                        "issue_severity": "LOW",
                        "filename": "app/x.py",
                        "line_number": 9,
                        "issue_text": "assert used",
                    },
                ]
            }
        )
    )
    trivy = tmp_path / "trivy.json"
    trivy.write_text(
        json.dumps(
            {
                "Results": [
                    {
                        "Vulnerabilities": [
                            {
                                "VulnerabilityID": "CVE-1",
                                "Severity": "CRITICAL",
                                "PkgName": "openssl",
                                "InstalledVersion": "1",
                                "FixedVersion": "2",
                            },
                            {
                                "VulnerabilityID": "CVE-2",
                                "Severity": "CRITICAL",
                                "PkgName": "zlib",
                                "InstalledVersion": "1",
                                "FixedVersion": "",
                            },
                        ]
                    }
                ]
            }
        )
    )

    findings = security_gate.bandit_findings(bandit) + security_gate.trivy_findings(trivy)
    blocking = {f["id"] for f in findings if security_gate.is_blocking(f)}

    assert blocking == {"B602", "CVE-1"}  # low bandit + unfixable CVE do not block


def test_redact_removes_secrets():
    fake_key = "AKIA" + "ABCDEFGHIJKLMNOP"  # built in two parts so secret scanners ignore it
    text = f"{fake_key} password=hunter2 account 123456789012"
    clean = ai_log_analyzer.redact(text)
    assert "AKIA" not in clean and "hunter2" not in clean and "123456789012" not in clean


def test_extract_relevant_keeps_error_lines():
    log = "\n".join([f"line {i}" for i in range(500)] + ["ERROR: boom"] + ["ok"] * 100)
    excerpt = ai_log_analyzer.extract_relevant(log)
    assert "ERROR: boom" in excerpt
    assert "line 10\n" not in excerpt  # unrelated early lines are dropped


def test_full_run_with_fake_bedrock(tmp_path, monkeypatch):
    log = tmp_path / "failed.log"
    log.write_text("FAILED tests/test_app.py::test_health - AssertionError\n")
    fake = json.dumps(
        {
            "failed_stage": "tests",
            "summary": "A unit test failed.",
            "root_cause": "The /health endpoint changed.",
            "evidence": ["FAILED tests/..."],
            "troubleshooting_steps": ["Run pytest locally"],
            "suggested_fix": "Revert the change",
            "confidence": "high",
            "needs_more_info": [],
        }
    )
    monkeypatch.setattr(ai_log_analyzer, "call_bedrock", lambda *a: fake)
    out = tmp_path / "ai.md"
    monkeypatch.setattr("sys.argv", ["x", "--log", str(log), "--out", str(out)])

    assert ai_log_analyzer.main() == 0
    report = out.read_text()
    assert "human must review" in report
    assert "The /health endpoint changed." in report


def test_report_is_written_even_if_bedrock_fails(tmp_path, monkeypatch):
    def broken(*args):
        raise RuntimeError("no credentials")

    log = tmp_path / "failed.log"
    log.write_text("Error: something broke\n")
    monkeypatch.setattr(ai_log_analyzer, "call_bedrock", broken)
    out = tmp_path / "ai.md"
    monkeypatch.setattr("sys.argv", ["x", "--log", str(log), "--out", str(out)])

    assert ai_log_analyzer.main() == 0
    assert "AI analysis was not available" in out.read_text()
