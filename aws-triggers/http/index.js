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

  // The lambda function, retrieved from a file in order to enable X-ray
  const fn = new aws.lambda.Function('HTTPTriggerLambda', {
    code: new pulumi.asset.AssetArchive({
      '__index.js': new pulumi.asset.FileAsset('../workloads/index.js'),
    }),
    handler: '__index.factorial', // Change to __index.<xyz> to change the lambda function
    runtime: aws.lambda.NodeJS12dXRuntime,
    role: role.arn,
    tracingConfig: {
      mode: 'Active', // Enable active X-ray
    },
  });

  // HTTP trigger
  return new awsx.apigateway.API('HTTPTrigger', {
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
