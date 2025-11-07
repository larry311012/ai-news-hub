import '/src/style.css'

/**
 * Shared Utility Functions for AI News Hub
 * Provides common functionality for error handling, validation, and data manipulation
 */

const API_BASE_URL = `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api`;

/**
 * Parse and handle API errors with user-friendly messages
 * @param {Error} error - Axios error object
 * @param {string} defaultMessage - Default message if specific error not found
 * @returns {string} User-friendly error message
 */
function handleApiError(error, defaultMessage = 'An error occurred') {
    if (error.response) {
        const status = error.response.status;
        const detail = error.response.data?.detail;
        const message = error.response.data?.message;

        switch (status) {
            case 400:
                return detail || message || 'Invalid request';
            case 401:
                return 'Your session has expired. Please login again.';
            case 403:
                return detail || 'Access denied';
            case 404:
                return detail || 'Resource not found';
            case 409:
                return detail || 'Conflict with existing data';
            case 422:
                return detail || 'Please check your input and try again';
            case 429:
                return 'Too many requests. Please try again later.';
            case 500:
                return 'Server error. Please try again later.';
            case 503:
                return 'Service temporarily unavailable. Please try again later.';
            default:
                return detail || message || defaultMessage;
        }
    } else if (error.request) {
        return 'Cannot connect to server. Please check your internet connection.';
    } else {
        return defaultMessage;
    }
}

/**
 * Show toast notification
 * @param {string} message - Message to display
 * @param {string} type - Type of toast (success, error, warning, info)
 * @param {number} duration - Duration in milliseconds
 */
function showToast(message, type = 'success', duration = 3000) {
    const toast = document.createElement('div');
    toast.className = `fixed top-4 right-4 z-50 max-w-sm px-6 py-4 rounded-lg shadow-lg transition-all transform translate-x-0 opacity-100`;

    const colors = {
        success: 'bg-green-500 text-white',
        error: 'bg-red-500 text-white',
        warning: 'bg-yellow-500 text-white',
        info: 'bg-blue-500 text-white'
    };

    toast.className += ` ${colors[type] || colors.info}`;

    const icons = {
        success: '✓',
        error: '✕',
        warning: '⚠',
        info: 'ℹ'
    };

    toast.innerHTML = `
        <div class="flex items-center space-x-2">
            <span class="text-xl font-bold">${icons[type] || icons.info}</span>
            <span class="font-medium">${message}</span>
        </div>
    `;

    document.body.appendChild(toast);

    // Slide in animation
    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease-out';
    }, 10);

    // Remove after duration
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease-in';
        setTimeout(() => {
            document.body.removeChild(toast);
        }, 300);
    }, duration);
}

/**
 * Validate email address
 * @param {string} email - Email to validate
 * @returns {boolean} True if valid
 */
function validateEmail(email) {
    if (!email) return false;
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

/**
 * Validate password strength
 * @param {string} password - Password to validate
 * @returns {Object} Validation result with isValid, strength, and errors
 */
function validatePassword(password) {
    const result = {
        isValid: true,
        strength: 0,
        errors: []
    };

    if (!password) {
        result.isValid = false;
        result.errors.push('Password is required');
        return result;
    }

    if (password.length < 8) {
        result.isValid = false;
        result.errors.push('Password must be at least 8 characters');
    } else {
        result.strength += 25;
    }

    if (password.length >= 12) {
        result.strength += 25;
    }

    if (/[A-Z]/.test(password)) {
        result.strength += 15;
    } else {
        result.isValid = false;
        result.errors.push('Password must contain at least one uppercase letter');
    }

    if (/[a-z]/.test(password)) {
        result.strength += 15;
    } else {
        result.isValid = false;
        result.errors.push('Password must contain at least one lowercase letter');
    }

    if (/[0-9]/.test(password)) {
        result.strength += 10;
    } else {
        result.isValid = false;
        result.errors.push('Password must contain at least one number');
    }

    if (/[^A-Za-z0-9]/.test(password)) {
        result.strength += 10;
    }

    return result;
}

/**
 * Calculate password strength percentage
 * @param {string} password - Password to check
 * @returns {number} Strength percentage (0-100)
 */
function getPasswordStrength(password) {
    if (!password) return 0;

    let strength = 0;

    // Length check
    if (password.length >= 8) strength += 25;
    if (password.length >= 12) strength += 25;

    // Contains uppercase
    if (/[A-Z]/.test(password)) strength += 15;

    // Contains lowercase
    if (/[a-z]/.test(password)) strength += 15;

    // Contains numbers
    if (/[0-9]/.test(password)) strength += 10;

    // Contains special characters
    if (/[^A-Za-z0-9]/.test(password)) strength += 10;

    return strength;
}

/**
 * Get password strength text
 * @param {number} strength - Strength percentage
 * @returns {string} Strength description
 */
function getPasswordStrengthText(strength) {
    if (strength === 0) return '';
    if (strength < 40) return 'Weak';
    if (strength < 70) return 'Fair';
    if (strength < 90) return 'Good';
    return 'Strong';
}

/**
 * Get password strength color class
 * @param {number} strength - Strength percentage
 * @returns {string} Tailwind color class
 */
function getPasswordStrengthColor(strength) {
    if (strength === 0) return 'bg-gray-200';
    if (strength < 40) return 'bg-red-500';
    if (strength < 70) return 'bg-yellow-500';
    if (strength < 90) return 'bg-blue-500';
    return 'bg-green-500';
}

/**
 * Parse JWT token
 * @param {string} token - JWT token
 * @returns {Object|null} Decoded token payload
 */
function parseJWT(token) {
    try {
        const base64Url = token.split('.')[1];
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
            return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
        }).join(''));

        return JSON.parse(jsonPayload);
    } catch (error) {
        console.error('Error parsing JWT:', error);
        return null;
    }
}

/**
 * Get auth token from storage
 * @returns {string|null} Auth token
 */
function getAuthToken() {
    // Check localStorage first (for remember_me), then sessionStorage
    return localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token');
}

/**
 * Set auth token in storage
 * @param {string} token - Auth token
 * @param {boolean} remember - Whether to use localStorage
 */
function setAuthToken(token, remember = false) {
    if (remember) {
        localStorage.setItem('auth_token', token);
        // Remove from sessionStorage if it exists
        sessionStorage.removeItem('auth_token');
    } else {
        sessionStorage.setItem('auth_token', token);
        // Remove from localStorage if it exists
        localStorage.removeItem('auth_token');
    }
}

/**
 * Remove auth token from storage
 */
function removeAuthToken() {
    localStorage.removeItem('auth_token');
    sessionStorage.removeItem('auth_token');
}

/**
 * Check if user is authenticated
 * @returns {boolean} True if authenticated
 */
function isAuthenticated() {
    const token = getAuthToken();
    if (!token) return false;

    const payload = parseJWT(token);
    if (!payload) return false;

    // Check if token is expired
    if (payload.exp && payload.exp * 1000 < Date.now()) {
        removeAuthToken();
        return false;
    }

    return true;
}

/**
 * Get current user from storage
 * @returns {Object|null} User object
 */
function getCurrentUser() {
    const userStr = localStorage.getItem('auth_user') || sessionStorage.getItem('auth_user');
    if (!userStr) return null;

    try {
        return JSON.parse(userStr);
    } catch (error) {
        console.error('Error parsing user data:', error);
        return null;
    }
}

/**
 * Set current user in storage
 * @param {Object} user - User object
 * @param {boolean} remember - Whether to use localStorage
 */
function setCurrentUser(user, remember = false) {
    const userStr = JSON.stringify(user);
    if (remember) {
        localStorage.setItem('auth_user', userStr);
        sessionStorage.removeItem('auth_user');
    } else {
        sessionStorage.setItem('auth_user', userStr);
        localStorage.removeItem('auth_user');
    }
}

/**
 * Check if user is guest
 * @returns {boolean} True if guest
 */
function isGuestUser() {
    return localStorage.getItem('is_guest') === 'true';
}

/**
 * Format date to relative time
 * @param {string|Date} date - Date to format
 * @returns {string} Relative time string
 */
function formatRelativeTime(date) {
    const now = new Date();
    const then = new Date(date);
    const diffMs = now - then;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`;
    if (diffDays < 365) return `${Math.floor(diffDays / 30)}mo ago`;
    return `${Math.floor(diffDays / 365)}y ago`;
}

/**
 * Format date to readable string
 * @param {string|Date} date - Date to format
 * @returns {string} Formatted date string
 */
function formatDate(date) {
    return new Date(date).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

/**
 * Debounce function
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {Function} Debounced function
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Get URL parameters
 * @returns {Object} URL parameters as key-value pairs
 */
function getUrlParams() {
    const params = {};
    const searchParams = new URLSearchParams(window.location.search);
    for (const [key, value] of searchParams) {
        params[key] = value;
    }
    return params;
}

/**
 * Redirect to URL with parameters
 * @param {string} url - Base URL
 * @param {Object} params - Parameters to append
 */
function redirectWithParams(url, params = {}) {
    const searchParams = new URLSearchParams(params);
    const paramString = searchParams.toString();
    window.location.href = paramString ? `${url}?${paramString}` : url;
}

/**
 * Copy text to clipboard
 * @param {string} text - Text to copy
 * @returns {Promise<boolean>} Success status
 */
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        return true;
    } catch (error) {
        // Fallback for older browsers
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        const success = document.execCommand('copy');
        document.body.removeChild(textarea);
        return success;
    }
}

/**
 * Sanitize HTML to prevent XSS
 * @param {string} html - HTML to sanitize
 * @returns {string} Sanitized HTML
 */
function sanitizeHtml(html) {
    const div = document.createElement('div');
    div.textContent = html;
    return div.innerHTML;
}

/**
 * Get user initials from name
 * @param {string} name - Full name
 * @returns {string} Initials
 */
function getUserInitials(name) {
    if (!name) return '?';
    const names = name.split(' ');
    if (names.length >= 2) {
        return (names[0][0] + names[names.length - 1][0]).toUpperCase();
    }
    return name.substring(0, 2).toUpperCase();
}

/**
 * Add CSS styles for animations
 */
(function addStyles() {
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideIn {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }

        @keyframes slideOut {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(100%);
                opacity: 0;
            }
        }

        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }

        @keyframes fadeOut {
            from { opacity: 1; }
            to { opacity: 0; }
        }
    `;
    document.head.appendChild(style);
})();

// Export functions for use in modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        API_BASE_URL,
        handleApiError,
        showToast,
        validateEmail,
        validatePassword,
        getPasswordStrength,
        getPasswordStrengthText,
        getPasswordStrengthColor,
        parseJWT,
        getAuthToken,
        setAuthToken,
        removeAuthToken,
        isAuthenticated,
        getCurrentUser,
        setCurrentUser,
        isGuestUser,
        formatRelativeTime,
        formatDate,
        debounce,
        getUrlParams,
        redirectWithParams,
        copyToClipboard,
        sanitizeHtml,
        getUserInitials
    };
}
