/**
 * Centralized API Client
 * Provides consistent API communication with error handling, retry logic, and request/response interceptors
 * Eliminates code duplication across 21+ files
 */

import { showToast } from './toast.js';

// API Base URL - Uses environment variable with fallback
// CRITICAL: In development, use empty string so Vite proxy handles requests
// In production, use full API URL
const isDevelopment = import.meta.env?.MODE === 'development' ||
                      import.meta.env?.VITE_ENV === 'development';

const API_BASE_URL = isDevelopment
    ? '' // Empty string = relative URLs, uses Vite proxy to avoid CORS
    : (import.meta.env?.VITE_API_URL || 'http://localhost:8000');

/**
 * Create API client with centralized configuration
 */
class ApiClient {
    constructor(baseURL = API_BASE_URL) {
        this.baseURL = baseURL;
        this.timeout = 30000; // 30 seconds default timeout
        this.retryAttempts = 3;
        this.retryDelay = 1000;
        this.csrfToken = null; // Store CSRF token
        this.csrfPromise = null; // Track in-progress CSRF fetch to avoid duplicate requests
    }

    /**
     * Build full URL with base URL
     */
    buildURL(endpoint) {
        if (endpoint.startsWith('http://') || endpoint.startsWith('https://')) {
            return endpoint;
        }
        return `${this.baseURL}${endpoint.startsWith('/') ? endpoint : '/' + endpoint}`;
    }

    /**
     * Fetch CSRF token from backend
     */
    async getCsrfToken() {
        // If we already have a token, return it
        if (this.csrfToken) {
            return this.csrfToken;
        }

        // If there's already a request in progress, wait for it
        if (this.csrfPromise) {
            return this.csrfPromise;
        }

        // Create a promise for the CSRF token fetch
        this.csrfPromise = (async () => {
            try {
                const response = await fetch(this.buildURL('/api/csrf-token'), {
                    method: 'GET',
                    credentials: 'include', // Important: send cookies
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });

                if (!response.ok) {
                    throw new Error('Failed to fetch CSRF token');
                }

                const data = await response.json();
                this.csrfToken = data.csrf_token;

                console.debug('[ApiClient] CSRF token obtained');

                return this.csrfToken;
            } catch (error) {
                console.error('[ApiClient] Failed to fetch CSRF token:', error);
                throw error;
            } finally {
                // Clear the promise so future requests can retry if needed
                this.csrfPromise = null;
            }
        })();

        return this.csrfPromise;
    }

    /**
     * Clear CSRF token (useful for token refresh)
     */
    clearCsrfToken() {
        this.csrfToken = null;
        this.csrfPromise = null;
    }

    /**
     * Make HTTP request with error handling and retry logic
     */
    async request(method, url, options = {}) {
        const fullURL = this.buildURL(url);
        const {
            data,
            headers = {},
            timeout = this.timeout,
            withCredentials = true,
            retries = this.retryAttempts,
            skipCsrf = false, // Allow skipping CSRF for specific requests
            skipAuth = false, // Allow skipping auth for login/register
            silent = false, // Suppress error toasts for graceful degradation
            ...fetchOptions
        } = options;

        // Fetch CSRF token for state-changing requests
        const needsCsrf = ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method.toUpperCase());
        if (needsCsrf && !skipCsrf) {
            try {
                await this.getCsrfToken();
            } catch (error) {
                console.error('[ApiClient] Failed to obtain CSRF token before request');
                throw new Error('Failed to obtain CSRF token. Please try again.');
            }
        }

        const config = {
            method: method.toUpperCase(),
            headers: {
                'Content-Type': 'application/json',
                ...headers
            },
            credentials: withCredentials ? 'include' : 'same-origin',
            ...fetchOptions
        };

        // Add CSRF token header for state-changing requests
        if (needsCsrf && !skipCsrf && this.csrfToken) {
            config.headers['X-CSRF-Token'] = this.csrfToken;
        }

        // Add body for POST, PUT, PATCH
        if (data && ['POST', 'PUT', 'PATCH'].includes(config.method)) {
            config.body = typeof data === 'string' ? data : JSON.stringify(data);
        }

        // Implement timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeout);
        config.signal = controller.signal;

        let lastError;
        for (let attempt = 0; attempt <= retries; attempt++) {
            try {
                const response = await fetch(fullURL, config);
                clearTimeout(timeoutId);

                // Handle response
                if (!response.ok) {
                    // If CSRF token is invalid (403), clear it and retry once
                    if (response.status === 403 && needsCsrf && attempt === 0) {
                        const errorText = await response.text();
                        if (errorText.toLowerCase().includes('csrf')) {
                            console.warn('[ApiClient] CSRF token invalid, refreshing...');
                            this.clearCsrfToken();
                            continue; // Retry with new token
                        }
                    }

                    await this.handleErrorResponse(response, silent);
                }

                // Parse JSON response
                const contentType = response.headers.get('content-type');
                if (contentType && contentType.includes('application/json')) {
                    const jsonData = await response.json();
                    return { data: jsonData, status: response.status, headers: response.headers };
                }

                // Return text for non-JSON responses
                const textData = await response.text();
                return { data: textData, status: response.status, headers: response.headers };

            } catch (error) {
                clearTimeout(timeoutId);
                lastError = error;

                // Don't retry on certain errors
                if (error.name === 'AbortError') {
                    throw new Error('Request timeout');
                }

                // Retry on network errors
                if (attempt < retries && this.shouldRetry(error)) {
                    await this.delay(this.retryDelay * (attempt + 1));
                    continue;
                }

                // Final failure
                if (!silent) {
                    this.handleNetworkError(error);
                }
                throw error;
            }
        }

        throw lastError;
    }

    /**
     * Check if we're currently on the auth page
     */
    isOnAuthPage() {
        const currentPath = window.location.pathname;
        return currentPath.includes('auth.html') ||
               currentPath.includes('login') ||
               currentPath === '/auth' ||
               currentPath.endsWith('/auth.html');
    }

    /**
     * Handle HTTP error responses
     */
    async handleErrorResponse(response, silent = false) {
        const { status } = response;
        let errorMessage = `HTTP ${status} Error`;

        try {
            const errorData = await response.json();

            // Handle standardized error format: { "error": { "message": "..." } }
            if (errorData.error && errorData.error.message) {
                errorMessage = errorData.error.message;
            }
            // Handle validation errors (422) which return an array of error objects
            else if (Array.isArray(errorData.detail)) {
                errorMessage = errorData.detail.map(err => err.msg || JSON.stringify(err)).join(', ');
            } else if (typeof errorData.detail === 'object' && errorData.detail !== null) {
                // Handle detail as object
                errorMessage = JSON.stringify(errorData.detail);
            } else {
                // Handle detail as string
                errorMessage = errorData.detail || errorData.message || errorMessage;
            }
        } catch (e) {
            // Couldn't parse error as JSON, use status text
            errorMessage = response.statusText || errorMessage;
        }

        // Handle specific status codes
        switch (status) {
            case 401:
                // Silent - app runs in anonymous mode by default
                // Users don't need to see auth warnings for local single-user deployment
                break;
            case 403:
                if (!silent) {
                    showToast('Access denied', 'error');
                }
                break;
            case 404:
                if (!silent) {
                    showToast('Resource not found', 'error');
                }
                break;
            case 429:
                if (!silent) {
                    showToast('Too many requests. Please try again later.', 'warning', 5000);
                }
                break;
            case 500:
            case 502:
            case 503:
                if (!silent) {
                    showToast('Server error. Please try again.', 'error');
                }
                break;
            default:
                if (status >= 400 && !silent) {
                    showToast(errorMessage, 'error');
                }
        }

        const error = new Error(errorMessage);
        error.status = status;
        error.response = response;
        throw error;
    }

    /**
     * Handle network errors
     */
    handleNetworkError(error) {
        if (error.message === 'Failed to fetch' || error.message.includes('NetworkError')) {
            showToast('Network error. Please check your connection.', 'error');
        } else if (error.message === 'Request timeout') {
            showToast('Request timed out. Please try again.', 'warning');
        }
    }

    /**
     * Determine if request should be retried
     */
    shouldRetry(error) {
        // Retry on network errors but not on client errors
        return error.message === 'Failed to fetch' ||
               error.message.includes('NetworkError') ||
               error.message === 'Request timeout';
    }

    /**
     * Delay helper for retry logic
     */
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    /**
     * HTTP method shortcuts
     */
    get(url, options = {}) {
        return this.request('GET', url, options);
    }

    post(url, data, options = {}) {
        return this.request('POST', url, { ...options, data });
    }

    put(url, data, options = {}) {
        return this.request('PUT', url, { ...options, data });
    }

    patch(url, data, options = {}) {
        return this.request('PATCH', url, { ...options, data });
    }

    delete(url, options = {}) {
        return this.request('DELETE', url, options);
    }

    /**
     * Upload file with progress tracking
     */
    async uploadFile(url, file, onProgress, options = {}) {
        const fullURL = this.buildURL(url);
        const formData = new FormData();
        formData.append('file', file);

        // Get CSRF token before upload
        await this.getCsrfToken();

        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();

            // Progress tracking
            if (onProgress) {
                xhr.upload.addEventListener('progress', (e) => {
                    if (e.lengthComputable) {
                        const percentComplete = (e.loaded / e.total) * 100;
                        onProgress(percentComplete);
                    }
                });
            }

            // Handle completion
            xhr.addEventListener('load', () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    try {
                        const data = JSON.parse(xhr.responseText);
                        resolve({ data, status: xhr.status });
                    } catch (e) {
                        resolve({ data: xhr.responseText, status: xhr.status });
                    }
                } else {
                    reject(new Error(`Upload failed: ${xhr.statusText}`));
                }
            });

            xhr.addEventListener('error', () => {
                reject(new Error('Upload failed: Network error'));
            });

            xhr.open('POST', fullURL);
            xhr.withCredentials = options.withCredentials !== false;

            // Add CSRF token header
            if (this.csrfToken) {
                xhr.setRequestHeader('X-CSRF-Token', this.csrfToken);
            }

            xhr.send(formData);
        });
    }
}

// Create singleton instance
const apiClient = new ApiClient();

// Export default instance and class
export default apiClient;
export { ApiClient, API_BASE_URL };

// Make available globally for HTML script tags
if (typeof window !== 'undefined') {
    window.apiClient = apiClient;
    window.ApiClient = ApiClient;
}
