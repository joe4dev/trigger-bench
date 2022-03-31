const AWSXRay = require('aws-xray-sdk');
const aws = AWSXRay.captureAWS(require('aws-sdk'));
AWSXRay.captureHTTPsGlobal(require('http'), true);
AWSXRay.captureHTTPsGlobal(require('https'), true);
const axios = require('axios');
const fs = require('fs').promises;

const getHttpLambda = (opts) => new Promise((resolve) => {
  // Start benchmark by issuing an HTTP request to the AWS APIGateway trigger using url param
  const { url } = opts;

  axios.get(url)
    .then(() => resolve({
      statusCode: 200,
      body: 'AWS - HTTP trigger benchmark successfully started',
      isBase64Encoded: false,
      headers: {
        'content-type': 'text/plain',
      },
    }))
    .catch((e) => resolve({
      statusCode: 200,
      body: `AWS - HTTP trigger benchmark failed to start\n\nError: ${e.message}`,
      isBase64Encoded: false,
      headers: {
        'content-type': 'text/plain',
      },
    }));
});

const getStorageLambda = (opts) => new Promise((resolve) => {
  const { bucketId } = opts;

  // Cannot use Pulumi dependencies inside a lambda, must rely on AWS SDk
  const s3Client = new aws.S3();

  // We are only allowed to write to /tmp inside a lambda
  fs.writeFile('/tmp/textfile.txt', 'Hello world!')
    .then(() => {
      fs.readFile('/tmp/textfile.txt').then((res) => {
        s3Client.putObject({
          Bucket: bucketId,
          Key: `${new Date().getTime()}.txt`, // Set current time as filename
          Body: res,
          ContentType: 'text/plain',
        }).promise()
          .then((data) => {
            resolve({
              statusCode: 200,
              body: 'AWS - Storage trigger benchmark successfully started',
              isBase64Encoded: false,
              headers: {
                'content-type': 'text/plain',
              },
            });
          }).catch((e) => {
            resolve({
              statusCode: 200,
              body: `AWS - Storage trigger benchmark failed to start\n\nError: ${e.message}`,
              isBase64Encoded: false,
              headers: {
                'content-type': 'text/plain',
              },
            });
          });
      }).catch((e) => {
        resolve({
          statusCode: 200,
          body: `AWS - Storage trigger benchmark failed to start\n\nError: ${e.message}`,
          isBase64Encoded: false,
          headers: {
            'content-type': 'text/plain',
          },
        });
      });
    })
    .catch((e) => {
      resolve({
        statusCode: 200,
        body: `AWS - Storage trigger benchmark failed to start\n\nError: ${e.message}`,
        isBase64Encoded: false,
        headers: {
          'content-type': 'text/plain',
        },
      });
    });
});

const getQueueLambda = (opts) => new Promise((resolve) => {
  const { queueUrl } = opts;

  // Cannot use Pulumi dependencies inside a lambda, must rely on AWS SDk
  const sqs = new aws.SQS({
    apiVersion: '2012-11-05',
  });

  // Build the message
  const params = {
    // Remove DelaySeconds parameter and value for FIFO queues
    DelaySeconds: 0,
    MessageSystemAttributes: {
      AWSTraceHeader: {
        DataType: 'String',
        // eslint-disable-next-line no-underscore-dangle
        StringValue: process.env._X_AMZN_TRACE_ID,
      },
    },
    MessageAttributes: {
      Title: {
        DataType: 'String',
        StringValue: 'Benchmark message',
      },
      Author: {
        DataType: 'String',
        StringValue: 'Benchmark',
      },
      WeeksOn: {
        DataType: 'Number',
        StringValue: '6',
      },
    },
    MessageBody: 'Hello world',
    // MessageDeduplicationId: "TheWhistler",  // Required for FIFO queues
    // MessageGroupId: "Group1",  // Required for FIFO queues
    QueueUrl: queueUrl,
  };

  // Send the message to the queue
  sqs.sendMessage(params).promise()
    .then(() => {
      resolve({
        statusCode: 200,
        body: 'AWS - Queue trigger benchmark successfully started',
        isBase64Encoded: false,
        headers: {
          'content-type': 'text/plain',
        },
      });
    })
    .catch((e) => {
      resolve({
        statusCode: 200,
        body: `AWS - Queue trigger benchmark failed to start\n\nError: ${e.message}`,
        isBase64Encoded: false,
        headers: {
          'content-type': 'text/plain',
        },
      });
    });
});

const fn = async (req, ctx) => {
  const triggerType = req.queryStringParameters && req.queryStringParameters.trigger;
  const validTrigger = triggerType && (triggerType === 'http' || triggerType === 'storage' || triggerType === 'queue');
  const triggerInput = req.queryStringParameters && req.queryStringParameters.input;

  if (validTrigger && triggerInput) {
    if (triggerType === 'http') {
      return getHttpLambda({ url: triggerInput });
    } if (triggerType === 'queue') {
      return getQueueLambda({ queueUrl: triggerInput });
    }

    // If not http or queue we have a storage trigger
    return getStorageLambda({ bucketId: triggerInput });
  }

  // Show error if params are not defined or not valid
  return {
    statusCode: 200,
    body: 'AWS - Benchmark failed to start\n\nError: Invalid query parameters',
    isBase64Encoded: false,
    headers: {
      'content-type': 'text/plain',
    },
  };
};

exports.handler = fn;
