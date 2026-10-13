"""Security gate: reads the Bandit and Trivy reports and decides PASS or FAIL.

Rules (edit SECURITY_POLICY below to make them stricter or looser):
  - Bandit (Python code):        fail on HIGH severity issues
  - Trivy  (container image):    fail on CRITICAL vulnerabilities that have a fix available

Accepted risks can be listed in security-exceptions.txt (one ID per line).
Exit code 0 = pass, 1 = fail (which stops the pipeline before deployment).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

SECURITY_POLICY = {
    "bandit_fail_on": {"HIGH"},
    "trivy_fail_on": {"CRITICAL"},
    "trivy_only_if_fix_available": True,
}


def load_json(path: Path):
    if not path.exists() or path.stat().st_size == 0:
        print(f"WARNING: {path} not found or empty")
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def bandit_findings(path: Path) -> list[dict]:
    data = load_json(path) or {}
    return [
        {
            "tool": "Bandit",
            "id": r.get("test_id", ""),
            "severity": r.get("issue_severity", "").upper(),
            "where": f"{r.get('filename')}:{r.get('line_number')}",
            "what": r.get("issue_text", ""),
            "fix": f"See https://bandit.readthedocs.io (rule {r.get('test_id')})",
        }
        for r in data.get("results", [])
    ]


def trivy_findings(path: Path) -> list[dict]:
    data = load_json(path) or {}
    out = []
    for result in data.get("Results") or []:
        for v in result.get("Vulnerabilities") or []:
            fixed = v.get("FixedVersion") or ""
            out.append(
                {
                    "tool": "Trivy",
                    "id": v.get("VulnerabilityID", ""),
                    "severity": v.get("Severity", "").upper(),
                    "where": f"{v.get('PkgName')} {v.get('InstalledVersion')}",
                    "what": (v.get("Title") or "")[:120],
                    "fix": f"Upgrade to {fixed}" if fixed else "No fix released yet",
                    "fixable": bool(fixed),
                }
            )
    return out


def is_blocking(f: dict) -> bool:
    if f["tool"] == "Bandit":
        return f["severity"] in SECURITY_POLICY["bandit_fail_on"]
    if f["tool"] == "Trivy":
        if f["severity"] not in SECURITY_POLICY["trivy_fail_on"]:
            return False
        return f.get("fixable", False) or not SECURITY_POLICY["trivy_only_if_fix_available"]
    return False


def load_exceptions(path: Path) -> set[str]:
    if not path.exists():
        return set()
    lines = (line.split("#", 1)[0].strip() for line in path.read_text().splitlines())
    return {line for line in lines if line}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bandit", default="reports/bandit.json")
    parser.add_argument("--trivy", default="reports/trivy.json")
    parser.add_argument("--exceptions", default="security-exceptions.txt")
    args = parser.parse_args()

    findings = bandit_findings(Path(args.bandit)) + trivy_findings(Path(args.trivy))
    exceptions = load_exceptions(Path(args.exceptions))
    blocking = [f for f in findings if is_blocking(f) and f["id"] not in exceptions]

    lines = ["## Security gate", "", f"Total findings: {len(findings)}", ""]
    if blocking:
        lines += [f"### FAILED - {len(blocking)} blocking finding(s)", ""]
        lines += ["| Tool | Severity | ID | Where | Issue | Fix |", "|---|---|---|---|---|---|"]
        for f in blocking:
            row = [f["tool"], f["severity"], f["id"], f"`{f['where']}`", f["what"], f["fix"]]
            lines.append("| " + " | ".join(row) + " |")
    else:
        lines.append("### PASSED - no blocking findings")
    text = "\n".join(lines) + "\n"
    print(text)

    # Show the result on the GitHub Actions run summary page
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as fh:
            fh.write(text)

    return 1 if blocking else 0


if __name__ == "__main__":
    sys.exit(main())
