import { showToast } from './utils/toast.js';
import api from './utils/api-client.js';
import logger from './utils/logger.js';
import { createApp } from 'vue'
import '/src/style.css'

// Initialize Vue app
const app = createApp({
    data() {
        return {
            currentUser: null,
            showUserMenu: false,
            isAuthenticated: false,
            loading: false,
            savedArticles: [],
            currentFilter: 'all',
            savedCount: 0,
            stats: {
                all: 0,
                today: 0,
                week: 0
            },
            removingArticle: null // Track which article is being removed for animation
        };
    },
    async mounted() {
        // Check authentication
        await this.verifyAuth();

        // Redirect if not authenticated
        if (!this.isAuthenticated) {
            showToast('Please sign in to view saved articles', 'warning');
            setTimeout(() => {
                window.location.href = 'auth.html?view=login&return=' + encodeURIComponent(window.location.pathname);
            }, 1500);
            return;
        }

        // Load saved articles
        await this.loadSavedArticles();

        // Close user menu when clicking outside
        document.addEventListener('click', (e) => {
            if (this.showUserMenu && !e.target.closest('.user-menu-container')) {
                this.showUserMenu = false;
            }
        });
    },
    watch: {
        currentFilter() {
            // Reload articles when filter changes
            this.loadSavedArticles();
        }
    },
    methods: {
        async verifyAuth() {
            try {
                const response = await api.get('/api/auth/me');
                this.currentUser = response.data;
                this.isAuthenticated = true;
            } catch (error) {
                // Token invalid or expired - clear auth data
                localStorage.removeItem('auth_token');
                sessionStorage.removeItem('auth_token');
                localStorage.removeItem('auth_user');
                sessionStorage.removeItem('auth_user');
                this.isAuthenticated = false;
                this.currentUser = null;
                logger.debug('User not authenticated:', error.message);
            }
        },

        async logout() {
            const confirmLogout = confirm('Are you sure you want to logout?');
            if (!confirmLogout) {
                return;
            }

            try {
                await api.post('/api/auth/logout', {});
                showToast('Successfully logged out', 'success');
            } catch (error) {
                logger.error('Logout error:', error);
            } finally {
                // Clear all auth data
                localStorage.removeItem('auth_token');
                sessionStorage.removeItem('auth_token');
                localStorage.removeItem('auth_user');
                sessionStorage.removeItem('auth_user');

                // Redirect to home
                window.location.href = 'index.html';
            }
        },

        getUserInitials(name) {
            if (!name) return '?';
            return name.split(' ')
                .map(n => n[0])
                .join('')
                .toUpperCase()
                .substring(0, 2);
        },

        toggleUserMenu() {
            this.showUserMenu = !this.showUserMenu;
        },

        /**
         * Load saved articles from API
         */
        async loadSavedArticles() {
            this.loading = true;
            try {
                const response = await api.get(`/api/articles/saved?filter=${this.currentFilter}`);
                this.savedArticles = response.data;

                // Update stats
                await this.updateStats();
            } catch (error) {
                logger.error('Error loading saved articles:', error);
                showToast('Failed to load saved articles', 'error');
            } finally {
                this.loading = false;
            }
        },

        /**
         * Update stats for filter tabs
         */
        async updateStats() {
            try {
                // Get count for each filter
                const allResponse = await api.get('/api/articles/saved?filter=all', { silent: true });
                const todayResponse = await api.get('/api/articles/saved?filter=today', { silent: true });
                const weekResponse = await api.get('/api/articles/saved?filter=week', { silent: true });

                this.stats = {
                    all: allResponse.data.length || 0,
                    today: todayResponse.data.length || 0,
                    week: weekResponse.data.length || 0
                };

                this.savedCount = this.stats.all;
            } catch (error) {
                logger.debug('Could not update stats:', error.message);
                this.stats = {
                    all: this.savedArticles.length,
                    today: 0,
                    week: 0
                };
            }
        },

        /**
         * Remove article from saved
         * @param {number} articleId - Article ID
         */
        async unsaveArticle(articleId) {
            // Trigger remove animation
            this.removingArticle = articleId;

            try {
                await api.delete(`/api/articles/save/${articleId}`);

                // Remove from local array with animation
                setTimeout(() => {
                    this.savedArticles = this.savedArticles.filter(a => a.id !== articleId);
                    this.savedCount = Math.max(0, this.savedCount - 1);
                    this.removingArticle = null;

                    showToast('Article removed from saved', 'success', 2000);

                    // Update stats
                    this.updateStats();
                }, 300);
            } catch (error) {
                this.removingArticle = null;
                logger.error('Error removing article:', error);
                showToast('Failed to remove article', 'error');
            }
        },

        /**
         * Select article for post generation and redirect
         * @param {Object} article - Article object
         */
        selectForGeneration(article) {
            // Redirect to main page with article selected
            window.location.href = `generating.html?article_ids=${article.id}`;
        },

        getCategoryColor(category) {
            const colors = {
                news: 'bg-blue-100 text-blue-800',
                research: 'bg-purple-100 text-purple-800',
                company: 'bg-green-100 text-green-800',
                newsletter: 'bg-yellow-100 text-yellow-800'
            };
            return colors[category] || 'bg-gray-100 text-gray-800';
        },

        formatDate(dateString) {
            const date = new Date(dateString);
            const now = new Date();
            const diffTime = Math.abs(now - date);
            const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

            if (diffDays === 0) return 'Today';
            if (diffDays === 1) return 'Yesterday';
            if (diffDays < 7) return `${diffDays}d ago`;
            return date.toLocaleDateString();
        },

        formatSaveDate(dateString) {
            const date = new Date(dateString);
            const now = new Date();
            const diffTime = Math.abs(now - date);
            const diffHours = Math.floor(diffTime / (1000 * 60 * 60));
            const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));

            if (diffHours < 1) {
                const diffMinutes = Math.floor(diffTime / (1000 * 60));
                return diffMinutes < 1 ? 'just now' : `${diffMinutes}m ago`;
            }
            if (diffHours < 24) return `${diffHours}h ago`;
            if (diffDays === 1) return 'yesterday';
            if (diffDays < 7) return `${diffDays}d ago`;
            return date.toLocaleDateString();
        },

        getDisplaySummary(article) {
            // For research articles, extract only the Abstract content
            if (article.category === 'research' && article.summary) {
                const abstractMatch = article.summary.match(/Abstract:\s*([\s\S]*?)(?:\n\n|$)/);
                if (abstractMatch && abstractMatch[1]) {
                    return abstractMatch[1].trim();
                }
                const abstractIndex = article.summary.indexOf('Abstract:');
                if (abstractIndex !== -1) {
                    return article.summary.substring(abstractIndex + 9).trim();
                }
            }
            return article.summary || 'No summary available';
        },

        trackArticleView(article) {
            // Track when user clicks "Read Article"
            if (window.analyticsClient) {
                window.analyticsClient.trackEvent('saved_article_view', {
                    article_id: article.id,
                    article_title: article.title,
                    source: article.source,
                    category: article.category
                });
            }
        }
    }
});

try {
    app.mount('#app');
    logger.info('Saved articles page mounted successfully');
} catch (error) {
    logger.error('Failed to mount saved articles page:', error);
    console.error('Vue mount error:', error);
}
