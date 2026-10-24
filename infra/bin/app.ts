import * as fs from 'node:fs';
import * as path from 'node:path';
import { App, Tags } from 'aws-cdk-lib';
import { GithubOidcStack } from '../lib/github-oidc-stack';
import { ExperimentConfig, LambdaBenchStack } from '../lib/lambda-bench-stack';

const BENCH_STACK_NAME = 'Seng533LambdaBench';

const experiment: ExperimentConfig & { region: string } = JSON.parse(
  fs.readFileSync(path.join(__dirname, '..', '..', 'config', 'experiment.json'), 'utf8'),
);

const app = new App();

// The account comes from the caller's credentials; it is never committed.
const env = { account: process.env.CDK_DEFAULT_ACCOUNT, region: experiment.region };

new GithubOidcStack(app, 'Seng533GithubOidc', {
  env,
  githubRepo: app.node.getContext('githubRepo'),
  githubOwnerId: app.node.getContext('githubOwnerId'),
  githubRepoId: app.node.getContext('githubRepoId'),
  githubDeployerId: app.node.getContext('githubDeployerId'),
  benchStackName: BENCH_STACK_NAME,
  // Pass -c githubOidcProviderArn=<arn> if the account already has a GitHub provider.
  existingProviderArn: app.node.tryGetContext('githubOidcProviderArn'),
});

new LambdaBenchStack(app, BENCH_STACK_NAME, { env, experiment });

Tags.of(app).add('Project', 'seng533');
