const aws = require('@pulumi/aws');

// Set roles and policies to ensure correct permissions
const role = new aws.iam.Role('DeveloperRole', {
  description: 'Developer role to use Amazon API Gateway.',
  forceDetachPolicies: false,
  maxSessionDuration: 3600,
  assumeRolePolicy: JSON.stringify({
    Version: '2012-10-17',
    Statement: [
      {
        Action: 'sts:AssumeRole',
        Principal: {
          Service: 'lambda.amazonaws.com',
        },
        Effect: 'Allow',
        Sid: '',
      },
      {
        Action: 'sts:AssumeRole',
        Principal: {
          Service: 'ops.apigateway.amazonaws.com',
        },
        Effect: 'Allow',
      },
    ],
  }),
}, {
  protect: false,
});

const policy = new aws.iam.Policy('AdministratorPolicy', {
  description: 'Provides full access to AWS services and resources.',
  path: '/',
  policy: {
    Version: '2012-10-17',
    Statement: [
      {
        Effect: 'Allow',
        Action: '*',
        Resource: '*',
      },
    ],
  },
}, {
  protect: false,
});

const rolePolicyAttachment = new aws.iam.RolePolicyAttachment('RolePolicy', {
  role,
  policyArn: policy.arn,
});

exports.roleId = role.id;
exports.policyId = policy.id;
exports.rolePolicyAttachmentId = rolePolicyAttachment.id;
