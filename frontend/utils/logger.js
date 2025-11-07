/**
 * Production-Safe Logger
 * Replaces console.log with conditional logging based on environment
 * Preserves console.error and console.warn for production debugging
 */

// Check if we're in development mode
const isDevelopment = () => {
    // Check multiple indicators
    if (typeof import.meta !== 'undefined' && import.meta.env) {
        return import.meta.env.DEV || import.meta.env.MODE === 'development';
    }
    if (typeof process !== 'undefined' && process.env) {
        return process.env.NODE_ENV === 'development';
    }
    // Default to checking hostname for localhost
    return window.location.hostname === 'localhost' ||
           window.location.hostname === '127.0.0.1' ||
           window.location.hostname === '';
};

/**
 * Logger class with conditional logging
 */
class Logger {
    constructor(namespace = '') {
        this.namespace = namespace;
        this.isDev = isDevelopment();
    }

    /**
     * Log only in development
     */
    log(...args) {
        if (this.isDev) {
            const prefix = this.namespace ? `[${this.namespace}]` : '';
            console.log(prefix, ...args);
        }
    }

    /**
     * Debug logs (development only, with timestamp)
     */
    debug(...args) {
        if (this.isDev) {
            const prefix = this.namespace ? `[${this.namespace}]` : '';
            const timestamp = new Date().toISOString();
            console.debug(`${timestamp} ${prefix}`, ...args);
        }
    }

    /**
     * Info logs (always shown, but styled)
     */
    info(...args) {
        const prefix = this.namespace ? `[${this.namespace}]` : '';
        console.info(prefix, ...args);
    }

    /**
     * Warning logs (always shown)
     */
    warn(...args) {
        const prefix = this.namespace ? `[${this.namespace}]` : '';
        console.warn(prefix, ...args);
    }

    /**
     * Error logs (always shown)
     */
    error(...args) {
        const prefix = this.namespace ? `[${this.namespace}]` : '';
        console.error(prefix, ...args);
    }

    /**
     * Table output (development only)
     */
    table(data) {
        if (this.isDev && console.table) {
            console.table(data);
        }
    }

    /**
     * Group logs together (development only)
     */
    group(label) {
        if (this.isDev && console.group) {
            console.group(label);
        }
    }

    groupEnd() {
        if (this.isDev && console.groupEnd) {
            console.groupEnd();
        }
    }

    /**
     * Performance timing
     */
    time(label) {
        if (this.isDev && console.time) {
            console.time(label);
        }
    }

    timeEnd(label) {
        if (this.isDev && console.timeEnd) {
            console.timeEnd(label);
        }
    }
}

// Create default logger instance
const logger = new Logger();

// Export both the class and default instance
export { Logger };
export default logger;

// Make available globally for HTML script tags
if (typeof window !== 'undefined') {
    window.Logger = Logger;
    window.logger = logger;

    // In production, override console.log to prevent accidental logging
    if (!isDevelopment()) {
        const originalLog = console.log;
        console.log = function(...args) {
            // Silently ignore, but keep in case we need to restore
            // Developers can still use console.error and console.warn
        };
        // Store original for debugging if needed
        console._originalLog = originalLog;
    }
}
