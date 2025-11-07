import { createApp } from 'vue'
import axios from 'axios'
import '/src/style.css'

createApp({
    data() {
        return {
            score: 0,
            recommendations: [],
            sessions: [],
            activity: [],
            activityFilter: 'all',
            loadingSessions: true,
            loadingActivity: true,
            savingSettings: false,
            settings: {
                notify_new_login: true,
                notify_password_change: true,
                notify_api_changes: true,
                session_timeout: 30
            },
            googleConnected: false,
            lastPasswordChange: 'Never',
            showChangePasswordModal: false,
            passwordForm: {
                current: '',
                new: '',
                confirm: ''
            },
            changingPassword: false,
            circumference: 2 * Math.PI * 70
        };
    },
    computed: {
        scoreColor() {
            if (this.score < 40) return '#ef4444'; // red
            if (this.score < 70) return '#f59e0b'; // yellow
            if (this.score < 90) return '#3b82f6'; // blue
            return '#10b981'; // green
        },
        scoreTextColor() {
            if (this.score < 40) return 'text-red-600';
            if (this.score < 70) return 'text-yellow-600';
            if (this.score < 90) return 'text-blue-600';
            return 'text-green-600';
        },
        scoreLabel() {
            if (this.score < 40) return 'Poor';
            if (this.score < 70) return 'Fair';
            if (this.score < 90) return 'Good';
            return 'Excellent';
        },
        filteredActivity() {
            if (this.activityFilter === 'all') return this.activity;
            return this.activity.filter(a => a.type === this.activityFilter);
        }
    },
    mounted() {
        // Configure axios to send httpOnly cookies
        axios.defaults.withCredentials = true;

        // Check authentication
        if (!isAuthenticated()) {
            window.location.href = 'auth.html';
            return;
        }

        this.loadSecurityData();
    },
    methods: {
        async loadSecurityData() {
            await Promise.all([
                this.loadSecurityScore(),
                this.loadSessions(),
                this.loadActivity(),
                this.loadSettings()
            ]);
        },

        async loadSecurityScore() {
            try {
                const token = getAuthToken();
                const response = await axios.get("/api/sessions/active", {
                withCredentials: true
            });

                this.score = response.data.score || 75;
                this.recommendations = response.data.recommendations || this.getDefaultRecommendations();
            } catch (error) {
                console.error('Error loading security score:', error);
                // Use mock data
                this.score = 75;
                this.recommendations = this.getDefaultRecommendations();
            }
        },

        async loadSessions() {
            this.loadingSessions = true;
            try {
                const token = getAuthToken();
                const response = await axios.get("/api/sessions/active", {
                withCredentials: true
            });

                this.sessions = response.data.sessions || this.getMockSessions();
            } catch (error) {
                console.error('Error loading sessions:', error);
                this.sessions = this.getMockSessions();
            } finally {
                this.loadingSessions = false;
            }
        },

        async loadActivity() {
            this.loadingActivity = true;
            try {
                const token = getAuthToken();
                const response = await axios.get("/api/sessions/active", {
                withCredentials: true
            });

                this.activity = response.data.activity || this.getMockActivity();
            } catch (error) {
                console.error('Error loading activity:', error);
                this.activity = this.getMockActivity();
            } finally {
                this.loadingActivity = false;
            }
        },

        async loadSettings() {
            try {
                const token = getAuthToken();
                const response = await axios.get("/api/sessions/active", {
                withCredentials: true
            });

                if (response.data) {
                    this.settings = response.data;
                    this.googleConnected = response.data.google_connected || false;
                    this.lastPasswordChange = response.data.last_password_change || 'Never';
                }
            } catch (error) {
                console.error('Error loading settings:', error);
            }
        },

        async saveSettings() {
            this.savingSettings = true;
            try {
                const token = getAuthToken();
                await axios.put(put, {
                withCredentials: true
            });

                if (typeof showToast === 'function') {
                    showToast('Security settings saved successfully', 'success');
                }
            } catch (error) {
                console.error('Error saving settings:', error);
                if (typeof showToast === 'function') {
                    showToast('Failed to save settings', 'error');
                }
            } finally {
                this.savingSettings = false;
            }
        },

        async revokeSession(sessionId) {
            try {
                const token = getAuthToken();
                await axios.delete("/api/sessions/revoke", {
                withCredentials: true
            });

                // Remove from list
                this.sessions = this.sessions.filter(s => s.id !== sessionId);

                if (typeof showToast === 'function') {
                    showToast('Session revoked successfully', 'success');
                }
            } catch (error) {
                console.error('Error revoking session:', error);
                if (typeof showToast === 'function') {
                    showToast('Failed to revoke session', 'error');
                }
            }
        },

        async revokeAllSessions() {
            if (!confirm('Are you sure you want to logout all other devices?')) return;

            try {
                const token = getAuthToken();
                await axios.post("/api/sessions/revoke", {
                withCredentials: true
            });

                // Keep only current session
                this.sessions = this.sessions.filter(s => s.is_current);

                if (typeof showToast === 'function') {
                    showToast('All other sessions logged out', 'success');
                }
            } catch (error) {
                console.error('Error revoking sessions:', error);
                if (typeof showToast === 'function') {
                    showToast('Failed to logout other sessions', 'error');
                }
            }
        },

        async changePassword() {
            if (this.passwordForm.new !== this.passwordForm.confirm) {
                if (typeof showToast === 'function') {
                    showToast('Passwords do not match', 'error');
                }
                return;
            }

            const validation = validatePassword(this.passwordForm.new);
            if (!validation.isValid) {
                if (typeof showToast === 'function') {
                    showToast(validation.errors[0], 'error');
                }
                return;
            }

            this.changingPassword = true;

            try {
                const token = getAuthToken();
                await axios.post("/api/sessions/revoke", {
                withCredentials: true
            });

                this.showChangePasswordModal = false;
                this.passwordForm = { current: '', new: '', confirm: '' };

                if (typeof showToast === 'function') {
                    showToast('Password changed successfully', 'success');
                }

                // Reload security score
                this.loadSecurityScore();
            } catch (error) {
                console.error('Error changing password:', error);
                if (error.response?.status === 401) {
                    if (typeof showToast === 'function') {
                        showToast('Current password is incorrect', 'error');
                    }
                } else {
                    if (typeof showToast === 'function') {
                        showToast('Failed to change password', 'error');
                    }
                }
            } finally {
                this.changingPassword = false;
            }
        },

        async linkOAuth(provider) {
            window.location.href = `${API_BASE_URL}/auth/oauth/${provider}?link=true`;
        },

        async unlinkOAuth(provider) {
            if (!confirm(`Are you sure you want to unlink your ${provider} account?`)) return;

            try {
                const token = getAuthToken();
                await axios.post("/api/sessions/revoke", {
                withCredentials: true
            });

                this.googleConnected = false;

                if (typeof showToast === 'function') {
                    showToast(`${provider} account unlinked`, 'success');
                }
            } catch (error) {
                console.error('Error unlinking OAuth:', error);
                if (typeof showToast === 'function') {
                    showToast('Failed to unlink account', 'error');
                }
            }
        },

        getActivityIcon(type) {
            const icons = {
                login: {
                    bg: 'bg-blue-100',
                    color: 'text-blue-600',
                    path: 'M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1'
                },
                password: {
                    bg: 'bg-yellow-100',
                    color: 'text-yellow-600',
                    path: 'M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z'
                },
                security: {
                    bg: 'bg-red-100',
                    color: 'text-red-600',
                    path: 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z'
                }
            };
            return icons[type] || icons.login;
        },

        getDefaultRecommendations() {
            return [
                { id: 1, text: 'Enable two-factor authentication' },
                { id: 2, text: 'Update your password' },
                { id: 3, text: 'Review active sessions' }
            ];
        },

        getMockSessions() {
            return [
                {
                    id: '1',
                    device: 'Chrome on MacOS',
                    location: '192.168.1.1',
                    last_activity: '2 minutes ago',
                    is_current: true
                },
                {
                    id: '2',
                    device: 'Safari on iPhone',
                    location: '192.168.1.2',
                    last_activity: '2 hours ago',
                    is_current: false
                }
            ];
        },

        getMockActivity() {
            return [
                {
                    id: '1',
                    type: 'login',
                    title: 'Successful login',
                    description: 'Chrome on MacOS from 192.168.1.1',
                    timestamp: '2 minutes ago',
                    success: true
                },
                {
                    id: '2',
                    type: 'password',
                    title: 'Password changed',
                    description: 'Your password was successfully updated',
                    timestamp: '2 days ago',
                    success: true
                },
                {
                    id: '3',
                    type: 'login',
                    title: 'Failed login attempt',
                    description: 'Chrome on Windows from 203.0.113.0',
                    timestamp: '3 days ago',
                    success: false
                }
            ];
        }
    }
}).mount('#security-app');
