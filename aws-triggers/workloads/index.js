// A simple function returning the factorial of a set number n
const factorial = (n) => {
  let res = 1;

  for (let i = 2; i <= n; i += 1) {
    res *= i;
  }
  return res;
};

// The handlers must be in a separate file due to using FileAsset
exports.factorial = async (req, ctx) => {
  const n = 20;
  return {
    statusCode: 200,
    body: `${n}! = ${factorial(n)}`,
    isBase64Encoded: false,
    headers: {
      'content-type': 'text/plain',
    },
  };
};

// Remove the last '/' and add '?number=<n>' to the end of the url to run
exports.factorialParam = async (req, ctx) => {
  const n = parseInt(req.queryStringParameters.number, 10);
  return {
    statusCode: 200,
    body: `${n}! = ${factorial(n)}`,
    isBase64Encoded: false,
    headers: {
      'content-type': 'text/plain',
    },
  };
};
