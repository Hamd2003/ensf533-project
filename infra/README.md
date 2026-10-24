# Infrastructure

The AWS side of the study, written with CDK which turns the code here into a CloudFormation template, and CloudFormation creates the resources in AWS.

## What it creates

**`Seng533LambdaBench`**, the experiment:

- 9 Lambda functions, one per workload × memory size: `seng533-{api,cpu,data}-{512,1024,1769}`.
- A public URL for each function. You call it with a plain HTTPS `POST`; no AWS account needed.
- A log group for each function, where AWS records how long each request took. Logs are kept for 90 days.

All 9 functions run the same Python code from [`../functions`](../functions). They only differ in which workload runs and how much memory they get.

**`Seng533GithubOidc`**, the access setup. Two roles let GitHub Actions use AWS without stored passwords or keys:

- **Deploy role:** only usable by runs the repo owner starts.
- **Export role:** read-only; any collaborator can use it to download measurement data.

This stack was deployed once by hand and rarely changes.

## How the config drives it

Everything comes from [`../config/experiment.json`](../config/experiment.json):

| Setting | What it controls |
|---|---|
| `region` | Where everything is deployed (`us-west-2`) |
| `workloads` × `memory_levels_mb` | Which functions exist (3 × 3 = 9) |
| `prime_limit`, `dataset_size`, `dataset_seed` | How much work each request does |

The file has `"frozen": true`: these values are final for the study.

## How it gets deployed

Only through GitHub Actions ([`deploy.yml`](../.github/workflows/deploy.yml)), never from a laptop:

1. Pushing to `main` shows a preview of what would change (the "diff") in the run summary.
2. The repo owner reviews it and starts the deploy manually.
3. A smoke test calls all 9 functions and checks their answers.

## Things to know

- **The URLs don't change.** Normal deploys keep the same URL for each function. They only change if a function is deleted and recreated.
- **URLs are private.** Anyone with a URL can call the function, and that uses our AWS budget. Never put a URL in GitHub (code, issues, PRs, commits).
- **Any deploy causes cold starts.** AWS restarts every function, and the first requests afterwards are slower. That's why nothing is deployed during a measurement round.
- **Concurrency limit.** The account can run a limited number of requests at once; above that, AWS replies with HTTP 429. That's a limit being hit, not a performance result.
- **Measurement data** comes from the **export-aws-data** workflow (Actions tab), not from AWS directly. See [`../docs/load-test-interface.md`](../docs/load-test-interface.md).
- **Deleting the stack** (`cdk destroy`) also deletes the logs. Export the data first. The URLs will be different if it's recreated.

## Files

| File | Purpose |
|---|---|
| `bin/app.ts` | Entry point: reads the config and creates both stacks |
| `lib/lambda-bench-stack.ts` | The 9 functions, their URLs and logs |
| `lib/github-oidc-stack.ts` | The GitHub Actions access roles |
| `cdk.json` | CDK settings and GitHub repo details |

To check the code locally without touching AWS: `npm ci && npx cdk synth Seng533LambdaBench`.
