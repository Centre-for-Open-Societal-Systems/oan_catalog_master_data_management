import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  scenarios: {
    registry_polling: {
      executor: "constant-vus",
      vus: Number(__ENV.VUS || 10),
      duration: __ENV.DURATION || "60s",
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<1000"],
  },
};

const baseUrl = __ENV.CATALOGUE_URL || "http://localhost:8000";
const token = __ENV.CATALOGUE_TOKEN || "";

export default function () {
  const headers = token ? { Authorization: `Bearer ${token}` } : {};
  const current = http.get(`${baseUrl}/v1/releases/current?country_code=ETH`, { headers });
  check(current, { "release is available": (response) => response.status === 200 });

  const etag = current.headers.Etag;
  if (etag) {
    const conditionalHeaders = { ...headers, "If-None-Match": etag };
    const snapshot = http.get(`${baseUrl}/v1/snapshots/current?country_code=ETH`, {
      headers: conditionalHeaders,
    });
    check(snapshot, { "conditional snapshot is unchanged": (response) => response.status === 304 });
  }
  sleep(1);
}
