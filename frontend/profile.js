import { showToast } from './utils/toast.js';
import api from './utils/api-client.js';
import logger from './utils/logger.js';
import { createApp } from 'vue'
import '/src/style.css'
import ApiKeyManager from './components/ApiKeyManager.js';

// API Key Manager Component will be registered after the main app
const app = createApp({
    data() {
        return {
            user: {
                name: 'John Doe',
                email: 'john@example.com',
                bio: '',
                profile_picture: null,
                created_at: new Date().toISOString(),
                last_login: new Date().toISOString(),
                email_verified: true,
                is_admin: false
            },
            stats: {
                bookmarked: 0,
                posts: 0,
                published: 0
            },
            editingProfile: false,
            changingPassword: false,
            saving: false,
            loading: true,
            profileForm: {
                name: '',
                email: '',
                bio: '',
                profile_picture: null
            },
            passwordForm: {
                currentPassword: '',
                newPassword: '',
                confirmPassword: '',
                showCurrent: false,
                showNew: false,
                showConfirm: false
            },
            deleteAccountPassword: '',
            showDeleteModal: false,
            sessionWarning: false,
            sessionTimeoutId: null,
            passwordStrength: 0
        };
    },
    computed: {
        userInitials() {
            const names = this.user.name.split(' ');
            if (names.length >= 2) {
                return (names[0][0] + names[names.length - 1][0]).toUpperCase();
            }
            return this.user.name.substring(0, 2).toUpperCase();
        },
        passwordStrengthText() {
            if (!this.passwordForm.newPassword) return '';
            if (this.passwordStrength < 40) return 'Weak';
            if (this.passwordStrength < 70) return 'Fair';
            if (this.passwordStrength < 90) return 'Good';
            return 'Strong';
        },
        passwordStrengthColor() {
            if (!this.passwordForm.newPassword) return 'bg-gray-200';
            if (this.passwordStrength < 40) return 'bg-red-500';
            if (this.passwordStrength < 70) return 'bg-yellow-500';
            if (this.passwordStrength < 90) return 'bg-blue-500';
            return 'bg-green-500';
        },
        accountAge() {
            if (!this.user.created_at) return 'N/A';
            const created = new Date(this.user.created_at);
            const now = new Date();
            const diffTime = Math.abs(now - created);
            const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

            if (diffDays < 30) return `${diffDays} days`;
            if (diffDays < 365) return `${Math.floor(diffDays / 30)} months`;
            return `${Math.floor(diffDays / 365)} years`;
        },
        lastActivityText() {
            if (!this.user.last_login) return 'N/A';
            const lastLogin = new Date(this.user.last_login);
            const now = new Date();
            const diffTime = Math.abs(now - lastLogin);
            const diffMinutes = Math.floor(diffTime / (1000 * 60));
            const diffHours = Math.floor(diffTime / (1000 * 60 * 60));
            const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));

            if (diffMinutes < 1) return 'Just now';
            if (diffMinutes < 60) return `${diffMinutes}m ago`;
            if (diffHours < 24) return `${diffHours}h ago`;
            if (diffDays < 7) return `${diffDays}d ago`;
            return this.formatDate(this.user.last_login);
        }
    },
    watch: {
        'passwordForm.newPassword': function(newVal) {
            this.calculatePasswordStrength(newVal);
        }
    },
    async mounted() {
        try {
            // Load data sequentially to ensure loading state is properly managed
            await this.loadUserData();
            await this.loadStats();
        } catch (error) {
            logger.error('Error during mount:', error);
            showToast('Failed to load profile data', 'error');
        } finally {
            // Ensure loading is always set to false
            this.loading = false;
        }
        this.setupSessionTimeout();
    },
    beforeUnmount() {
        if (this.sessionTimeoutId) {
            clearTimeout(this.sessionTimeoutId);
        }
    },
    methods: {
        async loadUserData() {
            try {
                logger.debug('Loading user data...');

                // Get user from localStorage (set during login)
                const storedUser = localStorage.getItem('auth_user');
                if (storedUser) {
                    const userData = JSON.parse(storedUser);
                    // Map full_name to name for frontend
                    this.user = {
                        ...userData,
                        name: userData.full_name || userData.name || 'User',
                        created_at: userData.created_at || new Date().toISOString(),
                        last_login: new Date().toISOString()
                    };
                }

                // Fetch latest user data from API
                try {
                    const response = await api.get('/api/auth/me');

                    // Map full_name to name for frontend compatibility
                    this.user = {
                        ...response.data,
                        name: response.data.full_name || response.data.name || 'User',
                        last_login: new Date().toISOString()
                    };
                    localStorage.setItem('auth_user', JSON.stringify(this.user));

                    logger.debug('User data loaded successfully');
                } catch (error) {
                    // If API fails, continue with localStorage data
                    logger.warn('Failed to fetch fresh user data, using cached data');
                }

            } catch (error) {
                logger.error('Error loading user data:', error);
                showToast('Failed to load user data', 'error');
            }
        },

        async loadStats() {
            try {
                logger.debug('Loading user stats...');

                const response = await api.get('/api/auth/stats');

                // Map backend response to frontend stats structure
                const data = response.data;

                this.stats = {
                    bookmarked: data.articles_count || data.bookmarked || 0,
                    posts: data.posts_count || data.posts || 0,
                    published: data.published_count || data.posts_count || data.published || 0
                };

                logger.debug('Stats loaded:', this.stats);

            } catch (error) {
                logger.warn('Error loading stats, using defaults:', error);
                // Use default stats if API call fails - stats are already initialized to 0
            }
        },

        async saveProfile() {
            this.saving = true;

            try {
                const response = await api.patch('/api/auth/profile', {
                    full_name: this.profileForm.name,
                    email: this.profileForm.email,
                    bio: this.profileForm.bio
                });

                // Map response back to frontend format
                this.user = {
                    ...response.data,
                    name: response.data.full_name || response.data.name || 'User'
                };
                localStorage.setItem('auth_user', JSON.stringify(this.user));
                this.editingProfile = false;

                showToast('Profile updated successfully!', 'success');
                logger.debug('Profile saved successfully');

            } catch (error) {
                logger.error('Error saving profile:', error);
                showToast('Failed to save profile. Please try again.', 'error');
            } finally {
                this.saving = false;
            }
        },

        async changePassword() {
            // Validate passwords
            if (this.passwordForm.newPassword.length < 8) {
                showToast('Password must be at least 8 characters', 'error');
                return;
            }
            if (!/[A-Z]/.test(this.passwordForm.newPassword)) {
                showToast('Password must contain at least one uppercase letter', 'error');
                return;
            }
            if (!/[a-z]/.test(this.passwordForm.newPassword)) {
                showToast('Password must contain at least one lowercase letter', 'error');
                return;
            }
            if (!/[0-9]/.test(this.passwordForm.newPassword)) {
                showToast('Password must contain at least one number', 'error');
                return;
            }
            if (this.passwordForm.newPassword !== this.passwordForm.confirmPassword) {
                showToast('Passwords do not match', 'error');
                return;
            }

            this.saving = true;

            try {
                await api.post('/api/auth/change-password', {
                    current_password: this.passwordForm.currentPassword,
                    new_password: this.passwordForm.newPassword
                });

                this.changingPassword = false;
                this.passwordForm = {
                    currentPassword: '',
                    newPassword: '',
                    confirmPassword: '',
                    showCurrent: false,
                    showNew: false,
                    showConfirm: false
                };

                showToast('Password changed successfully!', 'success');
                logger.debug('Password changed successfully');

            } catch (error) {
                logger.error('Error changing password:', error);

                if (error.status === 401) {
                    showToast('Current password is incorrect', 'error');
                } else {
                    showToast('Failed to change password. Please try again.', 'error');
                }
            } finally {
                this.saving = false;
            }
        },

        handleProfilePictureUpload(event) {
            const file = event.target.files[0];
            if (file) {
                // Validate file size (max 5MB)
                if (file.size > 5 * 1024 * 1024) {
                    showToast('File size must be less than 5MB', 'error');
                    return;
                }

                // Validate file type
                if (!file.type.startsWith('image/')) {
                    showToast('Please select a valid image file', 'error');
                    return;
                }

                this.profileForm.profile_picture = file;

                // Create preview
                const reader = new FileReader();
                reader.onload = (e) => {
                    this.user.profile_picture = e.target.result;
                };
                reader.readAsDataURL(file);

                showToast('Profile picture upload will be implemented in the backend', 'info');
            }
        },

        changeAvatar() {
            // Trigger file input
            const fileInput = document.getElementById('profile-picture-input');
            if (fileInput) {
                fileInput.click();
            }
        },

        editProfile() {
            this.editingProfile = true;
            this.profileForm = {
                name: this.user.name,
                email: this.user.email,
                bio: this.user.bio || '',
                profile_picture: null
            };
        },

        cancelEditProfile() {
            this.editingProfile = false;
        },

        cancelChangePassword() {
            this.changingPassword = false;
            this.passwordForm = {
                currentPassword: '',
                newPassword: '',
                confirmPassword: '',
                showCurrent: false,
                showNew: false,
                showConfirm: false
            };
        },

        confirmDeleteAccount() {
            this.showDeleteModal = true;
            this.deleteAccountPassword = '';
        },

        closeDeleteModal() {
            this.showDeleteModal = false;
            this.deleteAccountPassword = '';
        },

        async deleteAccount() {
            if (!this.deleteAccountPassword) {
                showToast('Please enter your password to confirm', 'error');
                return;
            }

            const confirmDelete = confirm('Are you ABSOLUTELY sure? This action cannot be undone!');
            if (!confirmDelete) {
                return;
            }

            this.saving = true;

            try {
                await api.delete('/api/auth/account', {
                    data: { password: this.deleteAccountPassword }
                });

                // Clear all stored data
                localStorage.clear();
                sessionStorage.clear();

                showToast('Account deleted successfully', 'success');
                logger.debug('Account deleted, redirecting to auth page');

                setTimeout(() => {
                    window.location.href = 'auth.html';
                }, 1500);

            } catch (error) {
                logger.error('Error deleting account:', error);

                if (error.status === 401) {
                    showToast('Incorrect password', 'error');
                } else {
                    showToast('Failed to delete account. Please try again.', 'error');
                }
            } finally {
                this.saving = false;
            }
        },

        goBack() {
            window.location.href = 'index.html';
        },

        formatDate(dateString) {
            if (!dateString) return 'N/A';
            const date = new Date(dateString);
            return date.toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'long',
                day: 'numeric'
            });
        },

        formatRelativeTime(dateString) {
            if (!dateString) return 'N/A';
            const date = new Date(dateString);
            const now = new Date();
            const diffTime = Math.abs(now - date);
            const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

            if (diffDays === 0) return 'Today';
            if (diffDays === 1) return 'Yesterday';
            if (diffDays < 7) return `${diffDays} days ago`;
            if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
            if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`;
            return `${Math.floor(diffDays / 365)} years ago`;
        },

        calculatePasswordStrength(password) {
            if (!password) {
                this.passwordStrength = 0;
                return;
            }

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

            this.passwordStrength = strength;
        },

        setupSessionTimeout() {
            // Show warning 5 minutes before session expires
            const warningTime = 25 * 60 * 1000; // 25 minutes (assuming 30 min session)

            this.sessionTimeoutId = setTimeout(() => {
                this.sessionWarning = true;
                showToast('Your session will expire in 5 minutes', 'warning', 10000);
            }, warningTime);
        }
    }
});

// Register API Key Manager component
app.component('api-key-manager', ApiKeyManager);

// Register OAuth Credentials Manager component (lazy load)
import('./components/OAuthCredentialsManager.js').then(module => {
    app.component('oauth-credentials-manager', module.default);
}).catch(err => {
    console.error('Failed to load OAuthCredentialsManager:', err);
});

// Register LinkedIn OAuth Connect component (lazy load)
import('./components/LinkedInOAuthConnect.js').then(module => {
    app.component('linkedin-oauth-connect', module.default);
}).catch(err => {
    console.error('Failed to load LinkedInOAuthConnect:', err);
});
// Register Twitter OAuth Connect component (lazy load)
import('./components/TwitterOAuthConnect.js').then(module => {
    app.component('twitter-oauth-connect', module.default);
}).catch(err => {
    console.error('Failed to load TwitterOAuthConnect:', err);
});

// Register Threads OAuth Connect component (lazy load)
import('./components/ThreadsOAuthConnect.js').then(module => {
    app.component('threads-oauth-connect', module.default);
}).catch(err => {
    console.error('Failed to load ThreadsOAuthConnect:', err);
});

// Register Instagram OAuth Connect component (lazy load)
import('./components/InstagramOAuthConnect.js').then(module => {
    app.component('instagram-oauth-connect', module.default);
}).catch(err => {
    console.error('Failed to load InstagramOAuthConnect:', err);
});

// Mount the app
app.mount('#profile-app');
