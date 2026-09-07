import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 100,
  duration: '30s',
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<200'],
  },
};

const BASE = __ENV.BASE_URL || 'http://localhost:8080';

export default function () {
  // P2-BM-03: 读接口现需 JWT（P1-CP-14），从 env 取 token
  const res = http.get(`${BASE}/api/v1/incidents`, {
    headers: { Authorization: `Bearer ${__ENV.JWT_TOKEN || ''}` },
  });
  check(res, { 'status is 200': (r) => r.status === 200 });
  sleep(0.05);
}