import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 10,
  duration: '15s',
};

const BASE = __ENV.BASE_URL || 'http://localhost:8080';

export default function () {
  const res = http.get(`${BASE}/api/v1/stream/incidents`);
  check(res, {
    'SSE status is 200': (r) => r.status === 200,
    'content-type is text/event-stream': (r) => (r.headers['Content-Type'] || '').includes('text/event-stream'),
  });
  sleep(1);
}