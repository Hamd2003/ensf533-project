// k6 load test for one setup (one of the 11 configurations in the proposal).
// Don't run this directly; use run.sh or round.sh (see README.md).
//
// Each VU sends POST requests back to back (zero think time) for 150 s.
// Requests sent in the first 30 s are labelled "warmup", the rest "measure".
// Every request is logged as one JSON line, which run.sh saves to results/.

import http from 'k6/http';
import exec from 'k6/execution';
import { Counter } from 'k6/metrics';

// Concurrency levels (virtual users) per profile. This is the only place they're defined.
//   standard   - the proposal: 10 VUs for RQ1/RQ3; 1 and 50 VUs for RQ2
//   restricted - plan adjustment for the account's current limit (10 concurrent executions,
//                100 requests/s). api does ~26 requests/s per VU, so 3 VUs is ~80 requests/s;
//                cpu-1024 at 8 VUs stays under 10 concurrent with headroom.
const PROFILES = {
  standard: { base: 10, low: 1, high: 50 },
  restricted: { base: 3, low: 1, high: 8 },
};

// The 11 setups: workload, memory (MB), concurrency level, key in urls.json.
// RQ1/RQ3 use the 9 "base" setups; RQ2 uses cpu-1024-low, cpu-1024 and cpu-1024-high.
const SETUPS = {
  'api-512': ['api', 512, 'base', 'UrlApi512'],
  'api-1024': ['api', 1024, 'base', 'UrlApi1024'],
  'api-1769': ['api', 1769, 'base', 'UrlApi1769'],
  'cpu-512': ['cpu', 512, 'base', 'UrlCpu512'],
  'cpu-1024': ['cpu', 1024, 'base', 'UrlCpu1024'],
  'cpu-1769': ['cpu', 1769, 'base', 'UrlCpu1769'],
  'data-512': ['data', 512, 'base', 'UrlData512'],
  'data-1024': ['data', 1024, 'base', 'UrlData1024'],
  'data-1769': ['data', 1769, 'base', 'UrlData1769'],
  'cpu-1024-low': ['cpu', 1024, 'low', 'UrlCpu1024'],
  'cpu-1024-high': ['cpu', 1024, 'high', 'UrlCpu1024'],
};

const SETUP = __ENV.SETUP;
if (!SETUPS[SETUP]) {
  throw new Error(`Unknown setup "${SETUP}". Use one of: ${Object.keys(SETUPS).join(', ')}`);
}
const [WORKLOAD, MEMORY_MB, LEVEL, URL_KEY] = SETUPS[SETUP];

// MODE=test: a 20 s check with 1 user, never study data. Otherwise PROFILE picks the VUs.
const TEST = __ENV.MODE === 'test';
const PROFILE = TEST ? 'test' : __ENV.PROFILE;
if (!TEST && !PROFILES[PROFILE]) {
  throw new Error(`Unknown profile "${PROFILE}". Use one of: ${Object.keys(PROFILES).join(', ')}`);
}
const VUS = TEST ? 1 : PROFILES[PROFILE][LEVEL];
const WARMUP_S = TEST ? 5 : 30;
const DURATION_S = TEST ? 20 : 150; // 30 s warm-up + 120 s measurement

// URLs are private: loadtest/urls.json is shared by the repo owner and ignored by git.
let urls;
try {
  urls = JSON.parse(open('./urls.json'));
} catch (e) {
  throw new Error('loadtest/urls.json is missing or invalid. Ask the repo owner for it.');
}
const URL = urls[URL_KEY];
if (!URL) throw new Error(`urls.json has no "${URL_KEY}"`);

// Request body and correct answers come from the shared, frozen experiment config.
const config = JSON.parse(open('../config/experiment.json'));
const BODY = JSON.stringify(config.request_body);
const EXPECTED = config.expected_results[WORKLOAD];

// Shown in k6's summary so problems are visible straight away.
const wrongAnswers = new Counter('wrong_or_failed_requests');

export const options = {
  scenarios: { run: { executor: 'constant-vus', vus: VUS, duration: `${DURATION_S}s` } },
  // Listing these makes the summary show measured-only response times and the failure count.
  thresholds: {
    'http_req_duration{phase:measure}': ['max>=0'],
    wrong_or_failed_requests: ['count>=0'],
  },
};

// True if two values have the same content. Ignores key order, which matters:
// k6's res.json() shuffles keys, so comparing JSON strings would reject correct answers.
function sameContent(a, b) {
  if (a === b) return true;
  if (typeof a !== 'object' || typeof b !== 'object' || a === null || b === null) return false;
  const ka = Object.keys(a);
  const kb = Object.keys(b);
  return ka.length === kb.length && ka.every((k) => sameContent(a[k], b[k]));
}

export default function () {
  const sentAt = Date.now();
  const phase = sentAt - exec.scenario.startTime < WARMUP_S * 1000 ? 'warmup' : 'measure';

  const res = http.post(URL, BODY, {
    headers: { 'content-type': 'application/json' },
    tags: { phase },
    timeout: '60s', // longer than the 30 s Lambda timeout, so Lambda timeouts show up as 5xx
  });

  let answer = null;
  try {
    answer = JSON.parse(res.body);
  } catch (e) {
    // not JSON: counts as a failed request
  }
  const valid = res.status === 200 && answer !== null && answer.ok === true
    && answer.workload === WORKLOAD && answer.memory_mb === MEMORY_MB
    && sameContent(answer.result, EXPECTED);
  if (!valid) wrongAnswers.add(1);

  // One line per request. request_id matches the AWS export, so analysis can join them exactly.
  console.log(JSON.stringify({
    profile: PROFILE,
    setup: SETUP,
    vus: VUS,
    t: sentAt,
    phase,
    vu: exec.vu.idInTest,
    status: res.status,
    error_code: res.error_code,
    duration_ms: res.timings.duration,
    valid,
    request_id: res.headers['X-Amzn-Requestid'] || null,
    env_id: answer && answer.env_id,
    cold: answer && answer.cold,
    compute_ms: answer && answer.compute_ms,
  }));
}
