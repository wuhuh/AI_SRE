import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  scenarios: {
    ramp: {
      executor: 'ramping-vus',
      stages: [
        { duration: '10s', target: 10 },
        { duration: '10s', target: 50 },
        { duration: '10s', target: 100 },
        { duration: '10s', target: 300 },
        { duration: '10s', target: 500 },
        { duration: '10s', target: 0 },
      ],
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<500'],
  },
};

const BASE = __ENV.BASE_URL || 'http://localhost:8080';

// P2-BM-03: 对齐现行契约 —— webhook 端点 + X-Webhook-Token
// （旧 /api/v1/alerts 现需 JWT，无头压测 100% 401）
export default function () {
  const payload = JSON.stringify({
    version: '4',
    status: 'firing',
    alerts: [{
      labels: { service: 'payment-service', alertname: 'latency_high', severity: 'P1' },
      annotations: { summary: 'payment p99 high' },
      startsAt: new Date().toISOString(),
    }],
  });
  const res = http.post(`${BASE}/api/v1/alerts/alertmanager`, payload, {
    headers: { 'Content-Type': 'application/json', 'X-Webhook-Token': __ENV.WEBHOOK_TOKEN || 'local-dev-webhook-token' },
  });
  check(res, { 'status is 202': (r) => r.status === 202 });
  sleep(0.1);
}