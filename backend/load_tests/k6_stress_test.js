/**
 * K6 Stress Testing Script for AI News Hub Backend
 *
 * Tests system under heavy load with 1000 concurrent users
 * Run with: k6 run load_tests/k6_stress_test.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const apiErrors = new Counter('api_errors');
const successfulRequests = new Counter('successful_requests');
const loginDuration = new Trend('login_duration');
const apiResponseTime = new Trend('api_response_time');

// Stress test configuration
export const options = {
  stages: [
    { duration: '2m', target: 100 },   // Ramp up to 100 users
    { duration: '3m', target: 500 },   // Ramp up to 500 users
    { duration: '5m', target: 1000 },  // Ramp up to 1000 users
    { duration: '5m', target: 1000 },  // Stay at 1000 users for 5 minutes
    { duration: '3m', target: 500 },   // Ramp down to 500 users
    { duration: '2m', target: 0 },     // Ramp down to 0 users
  ],
  thresholds: {
    http_req_duration: ['p(95)<2000', 'p(99)<5000'], // More lenient for stress test
    http_req_failed: ['rate<0.05'], // Allow up to 5% error rate
    errors: ['rate<0.10'], // Allow up to 10% custom errors
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

// Expanded test data for stress testing
const users = [];
for (let i = 1; i <= 50; i++) {
  users.push({
    email: `stresstest${i}@example.com`,
    password: 'Test123!@#',
  });
}

function getRandomUser() {
  return users[Math.floor(Math.random() * users.length)];
}

export function setup() {
  console.log('Setting up stress test users...');

  // Register users in batches
  const batchSize = 10;
  for (let i = 0; i < users.length; i += batchSize) {
    const batch = users.slice(i, i + batchSize);
    batch.forEach(user => {
      const registerRes = http.post(`${BASE_URL}/api/auth/register`, JSON.stringify({
        email: user.email,
        password: user.password,
        full_name: `Stress Test User ${user.email}`,
      }), {
        headers: { 'Content-Type': 'application/json' },
      });

      if (registerRes.status !== 200 && registerRes.status !== 400) {
        console.warn(`Failed to register ${user.email}: ${registerRes.status}`);
      }
    });

    // Small delay between batches
    sleep(0.5);
  }

  console.log(`Setup complete. ${users.length} users ready for stress testing.`);
  return { baseUrl: BASE_URL };
}

export default function(data) {
  const user = getRandomUser();

  // Random scenario selection for more realistic load
  const scenario = Math.random();

  if (scenario < 0.3) {
    // 30% - Read-heavy scenario (browsing)
    browsingScenario(data, user);
  } else if (scenario < 0.6) {
    // 30% - API interaction scenario
    apiInteractionScenario(data, user);
  } else if (scenario < 0.9) {
    // 30% - Social media scenario
    socialMediaScenario(data, user);
  } else {
    // 10% - Heavy load scenario (multiple rapid requests)
    heavyLoadScenario(data, user);
  }
}

function browsingScenario(data, user) {
  const token = login(data, user);
  if (!token) return;

  const authHeaders = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
  };

  // Browse articles
  for (let page = 1; page <= 5; page++) {
    const start = Date.now();
    const res = http.get(`${data.baseUrl}/api/articles?page=${page}&page_size=20`, {
      headers: authHeaders,
    });
    apiResponseTime.add(Date.now() - start);

    const success = check(res, {
      'articles loaded': (r) => r.status === 200,
    });

    if (success) {
      successfulRequests.add(1);
    } else {
      apiErrors.add(1);
      errorRate.add(1);
    }

    sleep(1);
  }

  // Browse posts
  for (let page = 1; page <= 3; page++) {
    const start = Date.now();
    const res = http.get(`${data.baseUrl}/api/posts?page=${page}&page_size=20`, {
      headers: authHeaders,
    });
    apiResponseTime.add(Date.now() - start);

    if (res.status === 200) {
      successfulRequests.add(1);
    } else {
      apiErrors.add(1);
    }

    sleep(1);
  }
}

function apiInteractionScenario(data, user) {
  const token = login(data, user);
  if (!token) return;

  const authHeaders = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
  };

  // Get profile
  let start = Date.now();
  let res = http.get(`${data.baseUrl}/api/auth/me`, { headers: authHeaders });
  apiResponseTime.add(Date.now() - start);
  if (res.status === 200) successfulRequests.add(1);
  else apiErrors.add(1);

  sleep(1);

  // Get API keys
  start = Date.now();
  res = http.get(`${data.baseUrl}/api/user-api-keys`, { headers: authHeaders });
  apiResponseTime.add(Date.now() - start);
  if (res.status === 200) successfulRequests.add(1);
  else apiErrors.add(1);

  sleep(1);

  // Get RSS feeds
  start = Date.now();
  res = http.get(`${data.baseUrl}/api/feeds`, { headers: authHeaders });
  apiResponseTime.add(Date.now() - start);
  if (res.status === 200) successfulRequests.add(1);
  else apiErrors.add(1);

  sleep(2);
}

function socialMediaScenario(data, user) {
  const token = login(data, user);
  if (!token) return;

  const authHeaders = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
  };

  // Get connections
  let start = Date.now();
  let res = http.get(`${data.baseUrl}/api/social-media/connections`, {
    headers: authHeaders,
  });
  apiResponseTime.add(Date.now() - start);
  if (res.status === 200) successfulRequests.add(1);
  else apiErrors.add(1);

  sleep(1);

  // Get platform status
  const platforms = ['twitter', 'linkedin', 'instagram', 'threads'];
  platforms.forEach(platform => {
    start = Date.now();
    res = http.get(`${data.baseUrl}/api/social-media/connections/status/${platform}`, {
      headers: authHeaders,
    });
    apiResponseTime.add(Date.now() - start);
    if (res.status === 200) successfulRequests.add(1);
    else apiErrors.add(1);

    sleep(0.5);
  });
}

function heavyLoadScenario(data, user) {
  const token = login(data, user);
  if (!token) return;

  const authHeaders = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
  };

  // Rapid fire requests
  const endpoints = [
    '/api/auth/me',
    '/api/articles?page=1&page_size=10',
    '/api/posts?page=1&page_size=10',
    '/api/social-media/connections',
    '/api/feeds',
    '/api/user-api-keys',
  ];

  endpoints.forEach(endpoint => {
    const start = Date.now();
    const res = http.get(`${data.baseUrl}${endpoint}`, {
      headers: authHeaders,
    });
    apiResponseTime.add(Date.now() - start);

    if (res.status === 200) {
      successfulRequests.add(1);
    } else {
      apiErrors.add(1);
      errorRate.add(1);
    }

    sleep(0.2); // Minimal delay
  });
}

function login(data, user) {
  const loginStart = Date.now();
  const loginRes = http.post(`${data.baseUrl}/api/auth/login`, JSON.stringify({
    email: user.email,
    password: user.password,
  }), {
    headers: { 'Content-Type': 'application/json' },
  });

  loginDuration.add(Date.now() - loginStart);

  const loginSuccess = check(loginRes, {
    'login successful': (r) => r.status === 200,
  });

  if (!loginSuccess) {
    errorRate.add(1);
    apiErrors.add(1);
    return null;
  }

  try {
    const token = JSON.parse(loginRes.body).access_token;
    successfulRequests.add(1);
    return token;
  } catch (e) {
    errorRate.add(1);
    apiErrors.add(1);
    return null;
  }
}

export function teardown(data) {
  console.log('Stress test completed');
}
