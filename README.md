# AI-Assisted Secure CI/CD Pipeline on AWS

A personal DevSecOps project: a Python app that goes from `git push` to **Amazon ECS** through a
**GitHub Actions** pipeline with automated tests, **Bandit** and **Trivy** security scans, and
infrastructure defined in **AWS CloudFormation** managed by **Sceptre**. When a build or
deployment fails, **Amazon Bedrock** reads the logs and suggests troubleshooting steps and a fix,
which a **human reviews** before any change is made. **Amazon CloudWatch** handles logs,
alarms and a dashboard.

## How it works

1. **Push / pull request** -> lint, unit tests, CloudFormation lint.
2. **Security** -> Bandit scans the Python code, Docker builds the image, Trivy scans the image,
   and a security gate fails the run on serious findings.
3. **Deploy (main only)** -> the scanned image is pushed to Amazon ECR, and Sceptre updates the
   CloudFormation stack, which rolls out the new version on ECS Fargate behind a load balancer.
4. **If anything fails** -> the AI Log Analysis workflow sends the failed logs (plus ECS and
   CloudWatch diagnostics) to Amazon Bedrock and posts the suggestion on the PR or as an issue,
   labelled `needs-human-review`.
5. **Human review** -> a person checks the suggestion, fixes it on a branch, and the PR must pass
   tests, scans and an approving review before merge.

See [docs/architecture.md](docs/architecture.md) for the diagram and security design.

## Project structure

```
.
├── .github/
│   ├── workflows/
│   │   ├── ci-cd.yml               # test -> scan -> deploy to ECS
│   │   └── ai-log-analysis.yml     # Bedrock analysis of failed runs
│   ├── CODEOWNERS                  # who must approve changes
│   └── pull_request_template.md    # human review checklist
├── app/
│   ├── __init__.py
│   ├── main.py                     # Flask API, JSON logs for CloudWatch
│   └── requirements.txt
├── tests/
│   ├── __init__.py
│   ├── test_app.py
│   └── test_pipeline_scripts.py
├── scripts/
│   ├── ai_log_analyzer.py          # Amazon Bedrock log analysis
│   ├── security_gate.py            # pass/fail rules for Bandit + Trivy
│   ├── test_bedrock.py             # quick Bedrock connection test
│   └── run_local_scans.ps1         # run the checks on Windows before pushing
├── infra/
│   ├── config/
│   │   ├── config.yaml             # Sceptre project settings
│   │   └── dev/
│   │       ├── config.yaml
│   │       ├── network.yaml
│   │       ├── ecr.yaml
│   │       ├── github-access.yaml
│   │       ├── app.yaml
│   │       └── monitoring.yaml
│   └── templates/                  # CloudFormation templates
│       ├── network.yaml
│       ├── ecr.yaml
│       ├── github-access.yaml
│       ├── ecs-app.yaml
│       └── monitoring.yaml
├── docs/
│   ├── architecture.md
│   ├── troubleshooting.md
│   └── runbook.md
├── Dockerfile
├── .dockerignore
├── .gitignore
├── pyproject.toml
├── requirements-dev.txt
├── requirements-infra.txt
├── security-exceptions.txt
└── README.md
```

## Run locally (Windows PowerShell)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt -r requirements-infra.txt
pytest
python -m app.main            # http://127.0.0.1:8080
.\scripts\run_local_scans.ps1
```

## Docs

- [Architecture and security design](docs/architecture.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Runbook (deploy, roll back, alarms, tear down)](docs/runbook.md)
