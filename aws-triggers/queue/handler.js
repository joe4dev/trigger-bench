const AWSXRay = require('aws-xray-sdk');

const sleep = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

const handler = async (event, context) => {
  const traceHeaderStr = event.Records[0].attributes.AWSTraceHeader;
  const traceData = AWSXRay.utils.processTraceData(traceHeaderStr);

  const segment = AWSXRay.getSegment();
  const subsegment = segment.addNewSubsegment('Annotations');
  subsegment.addAnnotation('AWSTraceHeader', traceData.root);
  subsegment.close();

  // Imitate workload
  await sleep(2000);

  return {};
};

exports.handler = handler;
