const AWSXRay = require('aws-xray-sdk');

// There will always be the `receiver0` subsegment to capture
// the first line of code and add trace annotations for certain event sources.
const numReceiverSubsegments = 5

// Generic event handler for TriggerBench receiver functions.
// Requires AWS X-Ray SDK for node: https://www.npmjs.com/package/aws-xray-sdk
const handler = async (event, context) => {
  // Add custom subsegment1
  const segment = AWSXRay.getSegment();
  const subsegment1 = segment.addNewSubsegment('receiver0');
  const traceHeader = parseTraceHeader(event);
  if (traceHeader) {
    addTraceAnnotations(subsegment1, traceHeader);
  }
  subsegment1.close();

  // Add additional receiver subsegments to measure XRay timestamp overhead
  for (let n = 1; n <= numReceiverSubsegments; n++) {
    const subN = segment.addNewSubsegment(`receiver${n}`);
    // Intentionally idle here
    subN.close()
  }

  return {
    statusCode: 200,
    body: 'Hello World!',
    isBase64Encoded: false,
    headers: {
      'content-type': 'text/plain',
    },
  };
};

// Returns an XRay trace header string for services where XRay trace correlation
// doesn't work with Lambda or null otherwise.
// Detect event source based on: https://stackoverflow.com/questions/41814750/how-to-know-event-souce-of-lambda-function-in-itself
function parseTraceHeader(event) {
  // Example Amazon SQS message event: https://docs.aws.amazon.com/lambda/latest/dg/with-sqs.html
  if (event.Records && (event.Records[0].eventSource === 'aws:sqs')) {
    // Extract trace data from AWS X-Ray header passed as message attribute
    return event.Records[0].attributes.AWSTraceHeader
  }
  return null;
};

// Add custom XRay annotations as described here:
// https://docs.aws.amazon.com/xray/latest/devguide/xray-sdk-nodejs-segment.html
// These trace annotations enable client-side trace correlation.
// Parameters:
// * subsegment: Custom XRay subsegment. See: https://docs.aws.amazon.com/xray/latest/devguide/xray-sdk-nodejs-subsegments.html
// * traceHeader: X-Amzn-Trace-Id tracing header string. See: https://docs.aws.amazon.com/xray/latest/devguide/xray-concepts.html#xray-concepts-tracingheader
function addTraceAnnotations(subsegment, traceHeader) {
  const traceData = AWSXRay.utils.processTraceData(traceHeader);
  // Add trace correlation annotation to subsegment.
  subsegment.addAnnotation('root_trace_id', traceData.root);
  subsegment.addAnnotation('parent_id', traceData.parent);
}

exports.handler = handler;
