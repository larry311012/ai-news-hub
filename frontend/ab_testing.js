/**
 * A/B Testing Client Library
 * Lightweight client for managing A/B test variant assignment and conversion tracking
 */

class ABTesting {
    constructor(apiBaseUrl = 'http://localhost:8000/api') {
        this.apiBaseUrl = apiBaseUrl;
        this.userId = null;
        this.sessionId = this.getOrCreateSessionId();
        this.experiments = {};
        this.initialized = false;

        // Load cached assignments from localStorage
        this.loadCachedAssignments();

    }

    /**
     * Get or create a persistent session ID
     * @returns {string} Session ID
     */
    getOrCreateSessionId() {
        let sessionId = localStorage.getItem('ab_session_id');

        if (!sessionId) {
            // Generate UUID-like session ID
            sessionId = 'session_' + this.generateUUID();
            localStorage.setItem('ab_session_id', sessionId);
        }

        return sessionId;
    }

    /**
     * Generate a simple UUID
     * @returns {string} UUID
     */
    generateUUID() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }

    /**
     * Load cached variant assignments from localStorage
     */
    loadCachedAssignments() {
        try {
            const cached = localStorage.getItem('ab_assignments');
            if (cached) {
                this.experiments = JSON.parse(cached);
            }
        } catch (error) {
            console.error('[A/B Testing] Error loading cached assignments:', error);
            this.experiments = {};
        }
    }

    /**
     * Save variant assignments to localStorage
     */
    saveCachedAssignments() {
        try {
            localStorage.setItem('ab_assignments', JSON.stringify(this.experiments));
        } catch (error) {
            console.error('[A/B Testing] Error saving cached assignments:', error);
        }
    }

    /**
     * Set user ID after authentication
     * @param {number} userId - User ID
     */
    setUserId(userId) {
        this.userId = userId;
    }

    /**
     * Get variant assignment for an experiment
     * @param {string} experimentName - Name of the experiment
     * @param {string[]} variants - Available variants (optional, for validation)
     * @returns {Promise<string>} Assigned variant
     */
    async getVariant(experimentName, variants = null) {
        // Check cache first
        if (this.experiments[experimentName]) {
            return this.experiments[experimentName];
        }

        try {
            // Request variant assignment from backend
            const response = await fetch(`${this.apiBaseUrl}/ab-testing/assign`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(this.getUserAuthHeader())
                },
                body: JSON.stringify({
                    experiment_name: experimentName,
                    session_id: this.sessionId
                })
            });

            if (!response.ok) {
                console.error(`[A/B Testing] Failed to assign variant for '${experimentName}'`);
                // Fallback to control variant
                return variants ? variants[0] : 'A';
            }

            const data = await response.json();
            const variant = data.variant;

            // Cache the assignment
            this.experiments[experimentName] = variant;
            this.saveCachedAssignments();

            console.log(`[A/B Testing] Assigned '${variant}' for '${experimentName}' - ${data.is_new_assignment ? '(new)' : '(existing)'}`);

            return variant;

        } catch (error) {
            console.error(`[A/B Testing] Error getting variant for '${experimentName}':`, error);
            // Fallback to control variant
            return variants ? variants[0] : 'A';
        }
    }

    /**
     * Track a conversion event
     * @param {string} experimentName - Name of the experiment
     * @param {string} eventName - Name of the conversion event
     * @param {object} properties - Optional additional properties
     * @returns {Promise<boolean>} Success status
     */
    async trackConversion(experimentName, eventName, properties = null) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/ab-testing/conversion`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(this.getUserAuthHeader())
                },
                body: JSON.stringify({
                    experiment_name: experimentName,
                    session_id: this.sessionId,
                    event_name: eventName,
                    properties: properties
                })
            });

            if (!response.ok) {
                console.error(`[A/B Testing] Failed to track conversion '${eventName}' for '${experimentName}'`);
                return false;
            }

            const data = await response.json();

            return data.success;

        } catch (error) {
            console.error(`[A/B Testing] Error tracking conversion for '${experimentName}':`, error);
            return false;
        }
    }

    /**
     * Check if an experiment is active
     * @param {string} experimentName - Name of the experiment
     * @returns {Promise<boolean>} True if experiment is active
     */
    async isExperimentActive(experimentName) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/ab-testing/experiments?active_only=true`, {
                headers: {
                    ...(this.getUserAuthHeader())
                }
            });

            if (!response.ok) {
                return false;
            }

            const experiments = await response.json();
            return experiments.some(exp => exp.name === experimentName && exp.is_active);

        } catch (error) {
            console.error(`[A/B Testing] Error checking experiment status:`, error);
            return false;
        }
    }

    /**
     * Get auth header if user is authenticated
     * @returns {object} Authorization header object
     */
    getUserAuthHeader() {
        const token = localStorage.getItem('token');
        if (token) {
            return { 'Authorization': `Bearer ${token}` };
        }
        return {};
    }

    /**
     * Get all active experiments
     * @returns {Promise<Array>} List of active experiments
     */
    async getActiveExperiments() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/ab-testing/experiments?active_only=true`, {
                headers: {
                    ...(this.getUserAuthHeader())
                }
            });

            if (!response.ok) {
                return [];
            }

            return await response.json();

        } catch (error) {
            console.error('[A/B Testing] Error fetching active experiments:', error);
            return [];
        }
    }

    /**
     * Get results for an experiment
     * @param {string} experimentName - Name of the experiment
     * @param {string} conversionEvent - Event to measure (default: signup_completed)
     * @returns {Promise<object>} Experiment results
     */
    async getExperimentResults(experimentName, conversionEvent = 'signup_completed') {
        try {
            const response = await fetch(
                `${this.apiBaseUrl}/ab-testing/results/${experimentName}?conversion_event=${conversionEvent}`,
                {
                    headers: {
                        ...(this.getUserAuthHeader())
                    }
                }
            );

            if (!response.ok) {
                return null;
            }

            return await response.json();

        } catch (error) {
            console.error(`[A/B Testing] Error fetching results for '${experimentName}':`, error);
            return null;
        }
    }

    /**
     * Clear cached assignments (for testing)
     */
    clearCache() {
        this.experiments = {};
        localStorage.removeItem('ab_assignments');
    }

    /**
     * Force reassignment (for testing - generates new session ID)
     */
    forceReassignment() {
        localStorage.removeItem('ab_session_id');
        localStorage.removeItem('ab_assignments');
        this.sessionId = this.getOrCreateSessionId();
        this.experiments = {};
    }
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ABTesting;
}

// Export as ES module
export default ABTesting;
