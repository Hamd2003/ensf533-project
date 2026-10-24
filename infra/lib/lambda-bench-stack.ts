import * as path from 'node:path';
import { CfnOutput, Duration, RemovalPolicy, Size, Stack, StackProps } from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as logs from 'aws-cdk-lib/aws-logs';
import { Construct } from 'constructs';

/** The keys of config/experiment.json this stack uses. */
export interface ExperimentConfig {
  memory_levels_mb: number[];
  workloads: string[];
  prime_limit: number;
  dataset_size: number;
  dataset_seed: number;
}

export interface LambdaBenchStackProps extends StackProps {
  experiment: ExperimentConfig;
}

const capitalize = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

/**
 * One function per (workload x memory) cell, each with its own public
 * Function URL. Fixed function names keep the URLs stable across deploys.
 */
export class LambdaBenchStack extends Stack {
  constructor(scope: Construct, id: string, props: LambdaBenchStackProps) {
    super(scope, id, props);
    const { experiment } = props;

    // One asset shared by all nine functions; only memorySize and handler differ.
    const code = lambda.Code.fromAsset(path.join(__dirname, '..', '..', 'functions'), {
      exclude: ['tests', '__pycache__'],
    });

    for (const workload of experiment.workloads) {
      for (const memory of experiment.memory_levels_mb) {
        const functionName = `seng533-${workload}-${memory}`;
        const cellId = `${capitalize(workload)}${memory}`;

        // Explicit log group so retention and removal are managed by the stack.
        const logGroup = new logs.LogGroup(this, `Logs${cellId}`, {
          logGroupName: `/aws/lambda/${functionName}`,
          retention: logs.RetentionDays.THREE_MONTHS,
          removalPolicy: RemovalPolicy.DESTROY,
        });

        // Never set reservedConcurrentExecutions here
        const fn = new lambda.Function(this, `Fn${cellId}`, {
          functionName,
          runtime: lambda.Runtime.PYTHON_3_12,
          architecture: lambda.Architecture.X86_64,
          handler: `${workload}.handler`,
          code,
          memorySize: memory,
          timeout: Duration.seconds(30),
          ephemeralStorageSize: Size.mebibytes(512),
          tracing: lambda.Tracing.DISABLED,
          loggingFormat: lambda.LoggingFormat.TEXT,
          logGroup,
          environment: {
            WORKLOAD: workload,
            PRIME_LIMIT: String(experiment.prime_limit),
            DATASET_SIZE: String(experiment.dataset_size),
            DATASET_SEED: String(experiment.dataset_seed),
          },
        });

        const url = fn.addFunctionUrl({
          authType: lambda.FunctionUrlAuthType.NONE,
          invokeMode: lambda.InvokeMode.BUFFERED,
        });

        // Stays in CloudFormation (not public); read locally and share privately.
        new CfnOutput(this, `Url${cellId}`, { value: url.url });
      }
    }
  }
}
