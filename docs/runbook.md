# Runbook - operating procedures

All `sceptre` commands run from the `infra` folder with your AWS admin profile active.

## Deploy a change (normal path)
1. Create a branch: `git checkout -b feature/my-change`
2. Make the change, run `.\scripts\run_local_scans.ps1`
3. Push and open a pull request. Wait for checks to pass.
4. A reviewer approves -> merge. The pipeline deploys to ECS automatically.
5. Check the run summary for the live URL and the CloudWatch dashboard.

## Respond to an AI log analysis issue / comment
1. Read the AI's root cause and **check it against the real logs** (links in the comment).
2. If you agree, fix it on a new branch and open a PR that links the issue.
3. Tick the human review checklist in the PR template.
4. Merge only after tests, scans and an approving review. Close the issue.
5. If the AI was wrong, write the real cause in the issue before closing it.

## Roll back
- Automatic: the ECS circuit breaker rolls back a release that never becomes healthy.
- Manual: revert the bad commit on main (`git revert <sha>`), open a PR and merge it. The pipeline redeploys the previous code with a new image.

## Respond to a CloudWatch alarm email
| Alarm | First check |
|---|---|
| high-cpu / high-memory | Dashboard -> traffic spike? Consider `DesiredCount: "2"` in `dev/app.yaml` |
| unhealthy-targets | `aws logs tail /ecs/secure-cicd-dev-app --since 15m` for crashes |
| http-5xx / app-errors | Dashboard "Latest app errors" widget, then logs |

## Update infrastructure
- App stack (`ecs-app.yaml`): change the template, open a PR -> merged = deployed by the pipeline.
- Foundation stacks: change the template, then run `sceptre launch -y dev/<stack>.yaml` yourself.
- Preview first: `sceptre --var "image_tag=<current sha>" diff dev/app.yaml`

## Rotate the GitHub CI keys (every 90 days)
```powershell
aws iam list-access-keys --user-name secure-cicd-github-ci
aws iam create-access-key --user-name secure-cicd-github-ci
# put the new keys in GitHub: Settings -> Environments -> aws-main -> secrets
aws iam delete-access-key --user-name secure-cicd-github-ci --access-key-id <OLD KEY ID>
```

## Pause to save money (keeps everything except the running app)
```powershell
cd infra
sceptre delete -y dev/monitoring.yaml
sceptre delete -y dev/app.yaml
```
Push any commit to main to bring the app back, then relaunch monitoring.

## Tear down everything
```powershell
cd infra
sceptre delete -y dev/monitoring.yaml
sceptre delete -y dev/app.yaml
sceptre delete -y dev/github-access.yaml   # delete the CI user's access key first (see below)
sceptre delete -y dev/ecr.yaml
sceptre delete -y dev/network.yaml
```
