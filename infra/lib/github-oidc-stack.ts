import { CfnOutput, Duration, Stack, StackProps } from 'aws-cdk-lib';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';

export interface GithubOidcStackProps extends StackProps {
  /** "owner/repo", exactly as GitHub shows it. */
  githubRepo: string;
  /** Numeric GitHub IDs (immutable, unlike names): gh api repos/<owner>/<repo> --jq '.owner.id, .id' */
  githubOwnerId: string;
  githubRepoId: string;
  /** GitHub user ID of the only account allowed to deploy (gh api users/<login> --jq .id). */
  githubDeployerId: string;
  /** Name of the experiment stack the deploy role may describe. */
  benchStackName: string;
  /** ARN of an existing GitHub OIDC provider; an account can only have one per URL. */
  existingProviderArn?: string;
}

const GITHUB_OIDC_HOST = 'token.actions.githubusercontent.com';

/**
 * GitHub Actions -> AWS trust via OIDC (no long-lived keys). Deployed once from
 * a laptop with admin credentials; deploy.yml never touches this stack.
 *
 */
export class GithubOidcStack extends Stack {
  constructor(scope: Construct, id: string, props: GithubOidcStackProps) {
    super(scope, id, props);

    const provider = props.existingProviderArn
      ? iam.OidcProviderNative.fromOidcProviderArn(this, 'GithubProvider', props.existingProviderArn)
      : new iam.OidcProviderNative(this, 'GithubProvider', {
          url: `https://${GITHUB_OIDC_HOST}`,
          clientIds: ['sts.amazonaws.com'],
        });

    const [owner, repo] = props.githubRepo.split('/');
    const mainSub = `repo:${owner}@${props.githubOwnerId}/${repo}@${props.githubRepoId}:ref:refs/heads/main`;

    const assumedByWorkflow = (workflow: string, extra: Record<string, string> = {}) =>
      new iam.WebIdentityPrincipal(provider.oidcProviderArn, {
        StringEquals: {
          [`${GITHUB_OIDC_HOST}:aud`]: 'sts.amazonaws.com',
          [`${GITHUB_OIDC_HOST}:sub`]: mainSub,
          [`${GITHUB_OIDC_HOST}:repository_id`]: props.githubRepoId,
          [`${GITHUB_OIDC_HOST}:workflow`]: workflow,
          ...Object.fromEntries(Object.entries(extra).map(([k, v]) => [`${GITHUB_OIDC_HOST}:${k}`, v])),
        },
      });

    // Deploy role: only runs started by the deployer's account (actor_id)
    const deployRole = new iam.Role(this, 'DeployRole', {
      roleName: 'seng533-github-deploy',
      assumedBy: assumedByWorkflow('deploy', { actor_id: props.githubDeployerId }),
      maxSessionDuration: Duration.hours(1),
    });
    deployRole.addToPolicy(new iam.PolicyStatement({
      actions: ['sts:AssumeRole'],
      resources: [`arn:${this.partition}:iam::${this.account}:role/cdk-*`],
    }));
    // Lets the smoke test read the Function URLs from the stack outputs.
    deployRole.addToPolicy(new iam.PolicyStatement({
      actions: ['cloudformation:DescribeStacks'],
      resources: [
        `arn:${this.partition}:cloudformation:${this.region}:${this.account}:stack/${props.benchStackName}/*`,
      ],
    }));

    const exportRole = new iam.Role(this, 'ExportRole', {
      roleName: 'seng533-github-export',
      assumedBy: assumedByWorkflow('export-aws-data'),
      maxSessionDuration: Duration.hours(1),
    });
    exportRole.addToPolicy(new iam.PolicyStatement({
      actions: ['logs:FilterLogEvents', 'logs:DescribeLogGroups'],
      resources: [
        `arn:${this.partition}:logs:${this.region}:${this.account}:log-group:/aws/lambda/seng533-*`,
      ],
    }));
    exportRole.addToPolicy(new iam.PolicyStatement({
      actions: ['cloudwatch:GetMetricData'],
      resources: ['*'],
    }));

    new CfnOutput(this, 'DeployRoleArn', { value: deployRole.roleArn });
    new CfnOutput(this, 'ExportRoleArn', { value: exportRole.roleArn });
  }
}
