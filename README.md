# SENG 533: AWS Lambda performance study

How memory allocation, concurrency and workload type affect AWS Lambda response time and throughput. This README covers reproducing the **AWS side**: nine Python Lambda functions behind public Function URLs, deployed with AWS CDK from GitHub Actions. To call the functions and export AWS-side data, see [docs/load-test-interface.md](docs/load-test-interface.md).

## What gets deployed

| | |
|---|---|
| Region | `us-west-2` (from `config/experiment.json`) |
| Functions | `seng533-{api,cpu,data}-{512,1024,1769}`, one per workload × memory cell |
| Runtime | Python 3.12, x86_64, standard library only |
| Config | 30 s timeout, 512 MB ephemeral storage, X-Ray off, text log format, no reserved/provisioned concurrency, no SnapStart |
| Invocation | Lambda Function URL, auth `NONE`, `BUFFERED`, no API Gateway / VPC |
| Logs | `/aws/lambda/<function>`, 3-month retention |

All nine functions share one code asset ([functions/](functions/)); only the handler and `memorySize` differ. Workload sizes and expected results live in [config/experiment.json](config/experiment.json).

## Repository layout

| Path | Contents |
|---|---|
| `functions/` | Handlers (`api.py`, `cpu.py`, `data.py`), shared response contract (`common.py`), pytest tests |
| `infra/` | CDK app: `Seng533LambdaBench` (the experiment) and `Seng533GithubOidc` (GitHub → AWS trust) |
| `tools/` | `smoke_test.py` (post-deploy), `export_aws_data.py` (data export), `update_expected.py` (calibration) |
| `.github/workflows/` | `ci.yml`, `deploy.yml`, `export-aws-data.yml` |
| `config/experiment.json` | Shared experiment configuration |

## Local checks (no AWS credentials needed)

```sh
pip install pytest && pytest functions/tests
cd infra && npm ci && npx tsc --noEmit && npx cdk synth Seng533LambdaBench --quiet
```

## One-time setup

Requires AWS CLI v2, Node LTS and admin credentials for the account (`aws configure sso`).

1. Check the Lambda concurrency quota (new accounts can be as low as 10; the study needs 50 concurrent executions):
   ```sh
   aws lambda get-account-settings --region us-west-2 --query AccountLimit
   aws service-quotas get-service-quota --service-code lambda --quota-code L-B99A9384 --region us-west-2
   ```
2. Bootstrap CDK and deploy the OIDC stack (from `infra/`):
   ```sh
   npx cdk bootstrap aws://<ACCOUNT_ID>/us-west-2
   npx cdk deploy Seng533GithubOidc
   ```
   If the account already has a GitHub OIDC provider, add `-c githubOidcProviderArn=<arn>`. Note the `DeployRoleArn` and `ExportRoleArn` outputs.
3. Set three repository variables (Settings → Secrets and variables → Actions → Variables):
   ```sh
   gh variable set AWS_DEPLOY_ROLE_ARN --body "<DeployRoleArn>"
   gh variable set AWS_EXPORT_ROLE_ARN --body "<ExportRoleArn>"
   gh variable set EXPERIMENT_FREEZE --body false
   ```

No AWS keys are stored anywhere: workflows get short-lived credentials through OIDC. The repo is private on GitHub Free, so GitHub environments aren't used. The IAM trust policies do the access control instead (see `infra/lib/github-oidc-stack.ts`):

| Role | Accepted only from |
|---|---|
| `seng533-github-deploy` | this repo (by ID), `main`, workflow `deploy`, **runs started by the account in `githubDeployerId`** |
| `seng533-github-export` | this repo (by ID), `main`, workflow `export-aws-data`, any collaborator |

To find the IDs in `infra/cdk.json` for a different repo or deployer: `gh api repos/<owner>/<repo> --jq '.owner.id, .id'` and `gh api users/<login> --jq .id`.

## Deploying

`Seng533LambdaBench` is deployed only by [deploy.yml](.github/workflows/deploy.yml), and only the repo owner can run it:

1. **Diff:** a push to `main` that touches `infra/`, `functions/` or `config/experiment.json`, or **Actions → deploy → Run workflow** with mode `diff`. The job summary shows the `cdk diff` and the commit SHA.
2. **Deploy:** **Run workflow** with mode `deploy` and `commit` = the SHA from the diff you reviewed. It refuses to run if `main` has moved since then, if `EXPERIMENT_FREEZE=true`, or if anyone else started (or re-ran) it. It runs `cdk deploy`, then smoke-tests every function.

Function URLs are redacted from deploy logs and masked in the smoke test. Read them locally only:

```sh
aws cloudformation describe-stacks --stack-name Seng533LambdaBench --region us-west-2 \
  --query "Stacks[0].Outputs"
```

## Calibration

1. Invoke each function a few times and note `compute_ms` (and `Max Memory Used` for `data-512`).
2. Adjust `prime_limit` / `dataset_size` in `config/experiment.json`, then run `python3 tools/update_expected.py` to recompute `expected_results`.
3. Once agreed with the team, set `"frozen": true` and deploy once. Changing workload sizes after that invalidates earlier runs.

## Operations

- **Rounds:** set `EXPERIMENT_FREEZE=true` before a round and back to `false` after. Never deploy during a round.
- **Emergency brake** (suspected abuse of a public URL; never during a round):
  ```sh
  aws lambda put-function-concurrency --function-name <fn> --reserved-concurrent-executions 0 --region us-west-2
  aws lambda delete-function-concurrency --function-name <fn> --region us-west-2   # restore
  ```
  This is drift from the CDK stack. Remove it before the next round.
- **Teardown:** `npx cdk destroy Seng533LambdaBench` deletes the functions *and their log groups*. Export all data first. Recreating the stack produces new URLs.
