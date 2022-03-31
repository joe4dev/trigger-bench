const pulumi = require('@pulumi/pulumi');
const automation = require('@pulumi/pulumi/x/automation');
const aws = require('@pulumi/aws');
const awsx = require('@pulumi/awsx');

const getEndpoint = async () => {
  // Import shared resources
  const user = await automation.LocalWorkspace.create({})
    .then((ws) => ws.whoAmI()
      .then((i) => i.user));
  const shared = new pulumi.StackReference(`${user}/aws-shared/dev`);

  const roleId = shared.requireOutput('roleId');
  const role = aws.iam.Role.get('DeveloperRole', roleId);

  // The lambda function to trigger the different triggers
  const fn = new aws.lambda.Function('InfraLambda', {
    code: new pulumi.asset.AssetArchive({
      '__index.js': new pulumi.asset.FileAsset('./handler.js'),
      node_modules: new pulumi.asset.FileArchive('./node_modules'), // Automatically zipped when deploying
    }),
    handler: '__index.handler',
    runtime: aws.lambda.NodeJS12dXRuntime,
    role: role.arn,
    tracingConfig: {
      mode: 'Active', // Enable X-ray
    },
  });

  // This endpoint is used to start the different benchmarks
  return new awsx.apigateway.API('InfraEndpoint', {
    stageArgs: {
      xrayTracingEnabled: true, // Enable X-ray for API gateway
    },
    routes: [
      // Serve a simple REST API (using AWS Lambda)
      {
        path: '/',
        method: 'GET',
        eventHandler: fn,
      },
    ],
  });
};

exports.url = getEndpoint().then((endpoint) => endpoint.url);
