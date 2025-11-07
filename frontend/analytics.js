/**
 * Analytics Client for AI News Aggregator
 *
 * Tracks user behavior and conversion funnel events with privacy-focused approach.
 * Features:
 * - Batch event sending (every 5 seconds or 10 events)
 * - Offline queue with retry logic
 * - Do Not Track (DNT) support
 * - Anonymous session tracking for guests
 * - GDPR compliant (no PII, IP anonymization on backend)
 */

class AnalyticsClient {
    constructor(apiBaseUrl = 'http://localhost:8000/api') {
        this.apiBaseUrl = apiBaseUrl;
        this.queue = [];
        this.maxQueueSize = 50;
        this.batchSize = 10;
        this.flushInterval = 5000; // 5 seconds
        this.sessionId = this.getOrCreateSessionId();
        this.enabled = !this.isDNTEnabled();
        this.userId = null;
        this.flushTimer = null;

        // Start periodic flush
        if (this.enabled) {
            this.startPeriodicFlush();
        } else {}

        // Flush queue before page unload
        window.addEventListener('beforeunload', () => {
            this.flush(true); // Synchronous flush
        });

        // Track visibility changes (when user leaves/returns to tab)
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.flush();
            }
        });
    }

    /**
     * Check if Do Not Track is enabled
     */
    isDNTEnabled() {
        return navigator.doNotTrack === '1' ||
               window.doNotTrack === '1' ||
               navigator.msDoNotTrack === '1';
    }

    /**
     * Get or create anonymous session ID
     */
    getOrCreateSessionId() {
        let sessionId = localStorage.getItem('analytics_session_id');

        if (!sessionId) {
            // Generate random session ID
            sessionId = 'sess_' + this.generateId();
            localStorage.setItem('analytics_session_id', sessionId);
        }

        return sessionId;
    }

    /**
     * Generate random ID
     */
    generateId() {
        return Date.now().toString(36) + Math.random().toString(36).substr(2);
    }

    /**
     * Identify user (call after authentication)
     */
    identify(userId, traits = {}) {
        if (!this.enabled) return;

        this.userId = userId;

        // Track identification event
        this.track('user_identified', {
            ...traits,
            identified_at: new Date().toISOString()
        });
    }

    /**
     * Track page view
     */
    page(pageName, properties = {}) {
        if (!this.enabled) return;

        this.track('page_view', {
            page_name: pageName,
            page_url: window.location.href,
            page_path: window.location.pathname,
            referrer: document.referrer,
            ...properties
        });
    }

    /**
     * Track event
     */
    track(eventName, properties = {}) {
        if (!this.enabled) {
            return;
        }

        // Validate event name
        if (!eventName || typeof eventName !== 'string') {
            console.error('[Analytics] Invalid event name:', eventName);
            return;
        }

        // Create event object
        const event = {
            event_name: eventName,
            properties: {
                ...properties,
                session_id: this.sessionId,
                page_url: window.location.href,
                page_path: window.location.pathname,
                timestamp: new Date().toISOString(),
                screen_width: window.screen.width,
                screen_height: window.screen.height,
                viewport_width: window.innerWidth,
                viewport_height: window.innerHeight,
                user_agent: navigator.userAgent,
                language: navigator.language
            },
            timestamp: new Date().toISOString()
        };

        // Add to queue
        this.queue.push(event);

        // Check if we should flush
        if (this.queue.length >= this.batchSize) {
            this.flush();
        }

        // Prevent queue from growing too large
        if (this.queue.length > this.maxQueueSize) {
            console.warn('[Analytics] Queue size exceeded, dropping oldest events');
            this.queue = this.queue.slice(-this.maxQueueSize);
        }
    }

    /**
     * Start periodic flush
     */
    startPeriodicFlush() {
        if (this.flushTimer) {
            clearInterval(this.flushTimer);
        }

        this.flushTimer = setInterval(() => {
            if (this.queue.length > 0) {
                this.flush();
            }
        }, this.flushInterval);
    }

    /**
     * Flush events to backend
     */
    async flush(synchronous = false) {
        if (this.queue.length === 0) return;

        const eventsToSend = [...this.queue];
        this.queue = [];

        if (synchronous) {
            // Use sendBeacon for synchronous sending (during page unload)
            this.sendBeacon(eventsToSend);
        } else {
            // Use fetch for normal async sending
            await this.sendFetch(eventsToSend);
        }
    }

    /**
     * Send events using fetch (async)
     */
    async sendFetch(events) {
        try {
            const headers = {
                'Content-Type': 'application/json'
            };

            if (token) {
                // Cookies sent automatically with withCredentials
            }

            // Send events one by one (backend expects single events)
            const promises = events.map(event =>
                fetch(`${this.apiBaseUrl}/analytics/events`, {
                    method: 'POST',
                    headers: headers,
                    body: JSON.stringify(event)
                }).catch(err => {
                    console.error('[Analytics] Failed to send event:', err);
                    return null;
                })
            );

            await Promise.all(promises);

        } catch (error) {
            console.error('[Analytics] Flush error:', error);
            // Re-queue failed events (at the front)
            this.queue.unshift(...events);
        }
    }

    /**
     * Send events using sendBeacon (synchronous during unload)
     */
    sendBeacon(events) {
        try {
            // sendBeacon can only send one request, so batch events
            const batchData = JSON.stringify({
                events: events,
                token: token,
                session_id: this.sessionId
            });

            // Note: sendBeacon has size limits (~64KB)
            // For production, consider chunking if needed
            const blob = new Blob([batchData], { type: 'application/json' });
            const sent = navigator.sendBeacon(`${this.apiBaseUrl}/analytics/events`, blob);

            if (sent) {} else {
                console.warn('[Analytics] sendBeacon failed (size limit?)');
            }

        } catch (error) {
            console.error('[Analytics] sendBeacon error:', error);
        }
    }

    /**
     * Clear session (useful for testing)
     */
    clearSession() {
        localStorage.removeItem('analytics_session_id');
        this.sessionId = this.getOrCreateSessionId();
    }

    /**
     * Enable/disable analytics
     */
    setEnabled(enabled) {
        this.enabled = enabled && !this.isDNTEnabled();

        if (this.enabled) {
            this.startPeriodicFlush();
        } else if (this.flushTimer) {
            clearInterval(this.flushTimer);
            this.flushTimer = null;
        }
    }

    /**
     * Get queue status (for debugging)
     */
    getStatus() {
        return {
            enabled: this.enabled,
            sessionId: this.sessionId,
            userId: this.userId,
            queueSize: this.queue.length,
            dnt: this.isDNTEnabled()
        };
    }
}

// Create singleton instance
const analytics = new AnalyticsClient();

// Expose to window for easy access
if (typeof window !== 'undefined') {
    window.analytics = analytics;
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = analytics;
}
