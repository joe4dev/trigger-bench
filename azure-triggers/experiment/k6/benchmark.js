import http from 'k6/http';
import exec from 'k6/execution';

export let options = {
  insecureSkipTLSVerify: true,
  noConnectionReuse: false,
  vus: 3,
  duration: '40s'
}

// 1. init code

export default function () {
  http.get(`${__ENV.BENCHMARK_URL}&id=${exec.scenario.iterationInTest}`);
}