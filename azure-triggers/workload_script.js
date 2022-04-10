import { check } from 'k6'
import http from 'k6/http'
import crypto from 'k6/crypto'

const benchmark_url = __ENV.BENCHMARK_URL

export default function() {
    const trace_header = getTraceHeader()
    const res = http.get(benchmark_url, {
        headers: {
            'traceparent': trace_header.header
        },	
        tags: { // Each request is tagged in the metrics with the corresponding trace header
            trace_header: trace_header.header,
        }
    });

    // to debug
    // console.log(JSON.stringify(res))
    // console.log(">>>>>> i am k6 in azure:" + trace_header.header)
    // console.log(">>>>>> response: " + res.status)

    check(res, {
        'status is 200': (res) => res.status === 200,
    })
}

function getTraceHeader() {
    const trace_id = crypto.hexEncode(crypto.randomBytes(16))
    const parent_id = crypto.hexEncode(crypto.randomBytes(8))

    return {
        trace_id: trace_id,
        header: `00-${trace_id}-${parent_id}-01`
    };
}
