# Troubleshooting

When the pipeline fails, the **AI Log Analysis** workflow posts a suggestion on the pull request (or opens an issue for `main`). Read it, then confirm it with the checks below. The AI can be wrong.

## Where to look

| What failed | Look here |
|---|---|
| Lint or tests | Actions run -> job "1. Lint and test" |
| Bandit / Trivy / security gate | Actions run -> job "2. Build and security scan" -> run summary + `security-reports` artifact |
| Deploy | Actions run -> job "3. Deploy" -> `deploy-diagnostics` artifact |
| App after deploy | CloudWatch -> Log groups -> `/ecs/secure-cicd-dev-app` |
| CloudFormation | CloudFormation console -> `secure-cicd-dev-app` -> Events tab |

## Common problems

### `Credentials could not be loaded` / `not authorized to perform: sts:AssumeRole`
- The secrets `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` are missing from the GitHub environment `aws-main`, or were copied with extra spaces.
- GitHub variable `AWS_DEPLOY_ROLE_ARN` or `AWS_AI_ROLE_ARN` is wrong or missing.
- The job is not running on `main`. The `aws-main` environment only allows the `main` branch.
- The access key was deleted or rotated in AWS but not updated in GitHub.

### Security gate failed
- Open the run summary: the table lists each blocking finding and the fix.
- Bandit HIGH: change the code (for example use `subprocess.run([...], shell=False)`).
- Trivy CRITICAL with a fix: rebuild to pick up the patched base image, or upgrade the package.
- If a finding is a false positive or an accepted risk, add its ID to `security-exceptions.txt` with a reason (needs review in the PR).

### `AccessDeniedException` from Bedrock
- In the Bedrock console (eu-north-1), open the model catalog, pick Claude Haiku 4.5 and run one test prompt in the playground. For Anthropic models, AWS asks first-time users to submit a short use-case form.
- Check `BEDROCK_MODEL_ID` = `eu.anthropic.claude-haiku-4-5-20251001-v1:0`.

### Deploy: stack `ROLLBACK_COMPLETE` on first creation
- Look at the CloudFormation Events tab for the first red `CREATE_FAILED` line.
- Delete the failed stack: `sceptre delete -y dev/app.yaml` (from `infra/`), fix, push again.

### Deploy: ECS circuit breaker rolled back
- `ecs-stopped-tasks.txt` in `deploy-diagnostics` shows why tasks stopped.
  - `CannotPullContainerError` -> image tag missing in ECR, or tasks have no internet route (check `AssignPublicIp: ENABLED`).
  - `Essential container exited` -> the app crashed. Check `cloudwatch-app-logs.txt`.
  - Health checks failing -> `/health` must return 200 on port 8080.

### Smoke test failed but the stack is fine
- The load balancer can take a minute after creation. Re-run the job.
- Test yourself: `curl http://<AppUrl>/health`.

## Useful commands (PowerShell)

```powershell
# Last 30 minutes of app logs
aws logs tail /ecs/secure-cicd-dev-app --since 30m --follow

# Why did tasks stop?
aws ecs describe-services --cluster secure-cicd-dev-cluster --services secure-cicd-dev-service --query "services[0].events[:10].message"

# Stack status
aws cloudformation describe-stacks --stack-name secure-cicd-dev-app --query "Stacks[0].StackStatus"

# Run the AI analysis yourself on any saved log
python scripts/ai_log_analyzer.py --log path\to\log.txt --out reports\ai-analysis.md
```
