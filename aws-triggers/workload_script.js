import { check } from 'k6';
import http from 'k6/http';

export default function () {
  const response = http.get(__ENV.URL);

  // to debug
  // console.log(JSON.stringify(res))
  console.log(response.body);

  check(response, {
    'status is 200': (res) => res.status === 200,
  });
}
