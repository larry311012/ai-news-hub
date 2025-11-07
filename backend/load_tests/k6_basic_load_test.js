/**
 * K6 Load Testing Script for AI News Hub Backend
 *
 * Tests basic load with 100 concurrent users
 * Run with: k6 run load_tests/k6_basic_load_test.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const loginDuration = new Trend('login_duration');
const postGenerationDuration = new Trend('post_generation_duration');

// Test configuration
export const options = {
  stages: [
    { duration: '1m', target: 20 },   // Ramp up to 20 users
    { duration: '3m', target: 100 },  // Ramp up to 100 users
    { duration: '5m', target: 100 },  // Stay at 100 users for 5 minutes
    { duration: '1m', target: 0 },    // Ramp down to 0 users
  ],
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'], // 95% of requests under 500ms, 99% under 1s
    http_req_failed: ['rate<0.01'], // Error rate should be less than 1%
    errors: ['rate<0.05'], // Custom error rate should be less than 5%
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

// Test data
const users = [
  { email: 'test1@example.com', password: 'Test123!@#' },
  { email: 'test2@example.com', password: 'Test123!@#' },
  { email: 'test3@example.com', password: 'Test123!@#' },
  { email: 'test4@example.com', password: 'Test123!@#' },
  { email: 'test5@example.com', password: 'Test123!@#' },
];

function getRandomUser() {
  return users[Math.floor(Math.random() * users.length)];
}

export function setup() {
  // Register test users if they don't exist
  console.log('Setting up test users...');
  users.forEach(user => {
    const registerRes = http.post(`${BASE_URL}/api/auth/register`, JSON.stringify({
      email: user.email,
      password: user.password,
      full_name: `Test User ${user.email}`,
    }), {
      headers: { 'Content-Type': 'application/json' },
    });

    if (registerRes.status !== 200 && registerRes.status !== 400) {
      console.warn(`Failed to register ${user.email}: ${registerRes.status}`);
    }
  });

  return { baseUrl: BASE_URL };
}

export default function(data) {
  const user = getRandomUser();

  // 1. Login
  const loginStart = Date.now();
  const loginRes = http.post(`${data.baseUrl}/api/auth/login`, JSON.stringify({
    email: user.email,
    password: user.password,
  }), {
    headers: { 'Content-Type': 'application/json' },
  });

  const loginSuccess = check(loginRes, {
    'login status is 200': (r) => r.status === 200,
    'login has access token': (r) => {
      try {
        return JSON.parse(r.body).access_token !== undefined;
      } catch (e) {
        return false;
      }
    },
  });

  errorRate.add(!loginSuccess);
  loginDuration.add(Date.now() - loginStart);

  if (!loginSuccess) {
    sleep(1);
    return;
  }

  const token = JSON.parse(loginRes.body).access_token;
  const authHeaders = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
  };

  sleep(1);

  // 2. Get user profile
  const profileRes = http.get(`${data.baseUrl}/api/auth/me`, {
    headers: authHeaders,
  });

  check(profileRes, {
    'profile status is 200': (r) => r.status === 200,
    'profile has email': (r) => {
      try {
        return JSON.parse(r.body).email !== undefined;
      } catch (e) {
        return false;
      }
    },
  });

  sleep(1);

  // 3. Get articles
  const articlesRes = http.get(`${data.baseUrl}/api/articles?page=1&page_size=10`, {
    headers: authHeaders,
  });

  check(articlesRes, {
    'articles status is 200': (r) => r.status === 200,
    'articles has items': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.items !== undefined;
      } catch (e) {
        return false;
      }
    },
  });

  sleep(1);

  // 4. Get posts
  const postsRes = http.get(`${data.baseUrl}/api/posts?page=1&page_size=10`, {
    headers: authHeaders,
  });

  check(postsRes, {
    'posts status is 200': (r) => r.status === 200,
  });

  sleep(2);

  // 5. Get social media connections
  const connectionsRes = http.get(`${data.baseUrl}/api/social-media/connections`, {
    headers: authHeaders,
  });

  check(connectionsRes, {
    'connections status is 200': (r) => r.status === 200,
  });

  sleep(1);
}

export function teardown(data) {
  console.log('Load test completed');
}
