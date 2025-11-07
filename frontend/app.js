import { showToast } from './utils/toast.js';
import api from './utils/api-client.js';
import logger from './utils/logger.js';
import { createApp } from 'vue'
import '/src/style.css'

// Initialize Vue app with NPM import
const app = createApp({
        data() {
            return {
                currentView: 'feed',
                loading: false,
                articles: [],
                posts: [],
                stats: null,
                selectedArticles: [],
                filters: {
                    search: '',
                    category: '',
                    source: '',
                    bookmarked: null
                },
                generatedContent: null,
                editableContent: {
                    twitter: '',
                    linkedin: '',
                    threads: ''
                },
                selectedPlatform: 'twitter',
                settings: {
                    aiProvider: 'openai',
                    apiKey: ''
                },
                // Generation button state
                isGenerating: false,
                generationButtonText: 'Generate Posts',
                // Generation screen state - IMPORTANT: These must be defined!
                showGeneratingScreen: false,
                platformStatus: {
                    linkedin: 'pending',
                    twitter: 'pending',
                    threads: 'pending'
                },
                generationStatus: {
                    linkedin: 'Waiting to start...',
                    twitter: 'Waiting to start...',
                    threads: 'Waiting to start...'
                },
                generationError: null,
                generationProgressMessage: 'Preparing to generate posts...',
                showTimeoutWarning: false,
                // Bookmark/Save state
                savedCount: 0,
                bookmarkAnimating: null // Track which article is currently animating
            };
        },
        computed: {
            uniqueSources() {
                return [...new Set(this.articles.map(a => a.source))].sort();
            },

            articlesByCategory() {
                // Group articles by category for better organization
                const grouped = {};
                this.articles.forEach(article => {
                    if (!grouped[article.category]) {
                        grouped[article.category] = [];
                    }
                    grouped[article.category].push(article);
                });
                return grouped;
            },

            displayArticles() {
                // If no category filter, return articles grouped by category (max 6 per category)
                // Otherwise return flat list
                if (!this.filters.category) {
                    const limited = {};
                    Object.keys(this.articlesByCategory).forEach(category => {
                        limited[category] = this.articlesByCategory[category].slice(0, 6);
                    });
                    return limited;
                }
                return { [this.filters.category]: this.articles };
            },

            shouldShowCategoryHeaders() {
                // Show category headers when viewing all categories
                return !this.filters.category && Object.keys(this.articlesByCategory).length > 1;
            },

            filteredStats() {
                // Calculate stats based on currently displayed articles
                if (!this.articles || this.articles.length === 0) {
                    return {
                        total: 0,
                        bookmarked: 0,
                        sources: 0
                    };
                }

                const bookmarkedCount = this.articles.filter(a => a.bookmarked).length;
                const uniqueSources = [...new Set(this.articles.map(a => a.source))];

                return {
                    total: this.articles.length,
                    bookmarked: bookmarkedCount,
                    sources: uniqueSources.length
                };
            }
        },
        async mounted() {

            // Check URL parameters for view selection
            const urlParams = new URLSearchParams(window.location.search);
            const viewParam = urlParams.get('view');
            if (viewParam === 'history') {
                this.currentView = 'history';
            }

            // Load app data directly (no auth required)
            this.loadArticles();
            this.loadStats();
            this.loadPosts();
            this.loadSettings();
            this.loadSavedCount();

            // Check for return from auth with pending action
            const returnAction = urlParams.get('action');
            if (returnAction === 'generate-post') {
                const articleIds = urlParams.get('articles');
                if (articleIds) {
                    this.selectedArticles = articleIds.split(',').map(id => parseInt(id));
                    await this.generatePosts();
                }
                // Clean up URL
                window.history.replaceState({}, '', window.location.pathname);
            }

        },
        methods: {
            async loadArticles() {
                try {
                    const params = new URLSearchParams();
                    if (this.filters.search) params.append('search', this.filters.search);
                    if (this.filters.category) params.append('category', this.filters.category);
                    if (this.filters.source) params.append('source', this.filters.source);

                    // Filter by bookmarked
                    if (this.filters.bookmarked !== null) {
                        params.append('bookmarked', this.filters.bookmarked);
                    }

                    // Increase limit to show diverse articles from all categories
                    // If filtering by specific category, use smaller limit
                    const limit = this.filters.category ? 100 : 500;
                    params.append('limit', limit);

                    const queryString = params.toString();
                    const url = `/api/articles?${queryString}`;

                    const response = await api.get(url, { skipAuth: true });
                    this.articles = response.data;
                } catch (error) {
                    logger.error('Error loading articles:', error);
                    showToast('Failed to load articles. Please try again.', 'error');
                }
            },

            async fetchArticles() {
                this.loading = true;
                try {
                    const response = await api.post('/api/articles/fetch', {
                        force_refresh: false
                    }, { skipAuth: true });

                    const newArticles = response.data.new_articles || 0;
                    const totalFetched = response.data.total_fetched || 0;

                    showToast(`Fetched ${totalFetched} articles (${newArticles} new)!`, 'success');
                    await this.loadArticles();
                    await this.loadStats();
                } catch (error) {
                    logger.error('Error fetching articles:', error);
                    showToast('Failed to fetch articles. Please try again.', 'error');
                } finally {
                    this.loading = false;
                }
            },

            async loadStats() {
                try {
                    const response = await api.get('/api/articles/stats/summary', { skipAuth: true });
                    this.stats = response.data;
                } catch (error) {
                    logger.error('Error loading stats:', error);
                    // Don't show error to user for stats - it's not critical
                }
            },

            async loadPosts() {
                try {
                    const response = await api.get('/api/posts', { skipAuth: true });
                    this.posts = response.data;
                } catch (error) {
                    logger.error('Error loading posts:', error);
                    // Don't show error to user for posts - it's not critical
                }
            },

            /**
             * Get default settings object
             * Used as fallback when settings endpoint fails
             */
            getDefaultSettings() {
                return {
                    aiProvider: 'openai',
                    apiKey: ''
                };
            },

            /**
             * Load user settings with graceful degradation
             * Settings are loaded lazily and don't block app initialization
             * If the endpoint fails, we use sensible defaults
             */
            async loadSettings() {
                try {
                    // Use silent mode to suppress error toasts
                    const response = await api.get('/api/settings', {
                        silent: true,
                        skipAuth: true
                    });
                    const settings = response.data;

                    // Load settings from backend
                    if (Array.isArray(settings)) {
                        settings.forEach(setting => {
                            if (setting.key === 'ai_provider') {
                                this.settings.aiProvider = setting.value;
                            } else if (setting.key === 'api_key') {
                                this.settings.apiKey = setting.value;
                            }
                        });
                        logger.debug('Settings loaded successfully');
                    } else {
                        logger.warn('Settings response format unexpected, using defaults');
                        this.settings = this.getDefaultSettings();
                    }
                } catch (error) {
                    // Graceful degradation: use default settings if endpoint fails
                    // This ensures the app continues to work even if settings are unavailable
                    logger.warn('Could not load settings, using defaults:', error.message);
                    this.settings = this.getDefaultSettings();

                    // Don't block the user - settings will be created when they first save
                    // Log for debugging but don't crash or show intrusive errors
                }
            },

            async saveSettings() {
                try {
                    // Save AI provider
                    await api.post('/api/settings', {
                        key: 'ai_provider',
                        value: this.settings.aiProvider,
                        encrypted: false
                    }, { skipAuth: true });

                    // Save API key (encrypted)
                    if (this.settings.apiKey) {
                        await api.post('/api/settings', {
                            key: 'api_key',
                            value: this.settings.apiKey,
                            encrypted: true
                        }, { skipAuth: true });
                    }

                    showToast('Settings saved successfully!', 'success');
                } catch (error) {
                    logger.error('Error saving settings:', error);
                    showToast('Failed to save settings. Please try again.', 'error');
                }
            },

            /**
             * Load count of saved articles
             * Updates the badge in navigation
             */
            async loadSavedCount() {
                try {
                    const response = await api.get('/api/articles/saved/count', { silent: true, skipAuth: true });
                    this.savedCount = response.data.count || 0;
                } catch (error) {
                    logger.debug('Could not load saved count:', error.message);
                    this.savedCount = 0;
                }
            },

            /**
             * Save or unsave an article
             * @param {Object} article - Article object
             */
            async saveArticle(article) {
                // Trigger bounce animation
                this.bookmarkAnimating = article.id;
                setTimeout(() => {
                    this.bookmarkAnimating = null;
                }, 300);

                try {
                    if (article.is_saved) {
                        // Unsave article
                        await api.delete(`/api/articles/save/${article.id}`, { skipAuth: true });
                        article.is_saved = false;
                        this.savedCount = Math.max(0, this.savedCount - 1);
                        showToast('Article removed from saved', 'success', 2000);
                    } else {
                        // Save article
                        await api.post('/api/articles/save', {
                            article_id: article.id,
                            article_title: article.title,
                            article_url: article.link
                        }, { skipAuth: true });
                        article.is_saved = true;
                        this.savedCount += 1;
                        showToast('Article saved!', 'success', 2000);
                    }

                    // Update article in the articles array to ensure reactivity
                    const articleIndex = this.articles.findIndex(a => a.id === article.id);
                    if (articleIndex !== -1) {
                        // Use Vue.set or direct assignment to ensure reactivity
                        this.articles[articleIndex].is_saved = article.is_saved;
                    }
                } catch (error) {
                    logger.error('Error saving article:', error);
                    showToast('Failed to save article. Please try again.', 'error');
                }
            },

            /**
             * Check if an article is saved
             * @param {number} articleId - Article ID
             * @returns {boolean}
             */
            checkIfSaved(articleId) {
                const article = this.articles.find(a => a.id === articleId);
                return article ? article.is_saved : false;
            },

            async toggleBookmark(articleId) {
                // Legacy method - find article and call saveArticle
                const article = this.articles.find(a => a.id === articleId);
                if (article) {
                    await this.saveArticle(article);
                }
            },

            toggleSelect(articleId) {
                const index = this.selectedArticles.indexOf(articleId);
                if (index === -1) {
                    this.selectedArticles.push(articleId);
                } else {
                    this.selectedArticles.splice(index, 1);
                }
            },

            async generatePosts() {
                if (this.selectedArticles.length === 0) {
                    showToast('Please select at least one article', 'warning');
                    return;
                }

                // IMMEDIATE FEEDBACK - Update button state instantly
                this.isGenerating = true;
                this.generationButtonText = 'Starting...';
                this.loading = true;

                // OPTIMISTIC REDIRECT - Go to loading page immediately
                // The generating.html page will handle the API call
                try {
                    // Update button to show we're redirecting
                    this.generationButtonText = 'Redirecting...';

                    // Redirect almost immediately (just 200ms for button animation)
                    setTimeout(() => {
                        // Pass article IDs to generating page via URL
                        const articleIds = this.selectedArticles.join(',');
                        window.location.href = `generating.html?article_ids=${articleIds}`;
                    }, 200);

                } catch (error) {
                    logger.error('Error redirecting:', error);

                    // Reset button state on error
                    this.isGenerating = false;
                    this.generationButtonText = 'Generate Posts';
                    this.loading = false;

                    showToast('Failed to start generation. Please try again.', 'error');
                }
            },

            async regenerateContent() {
                showToast('Regenerating content...', 'info');
                await this.generatePosts();
            },

            async saveDraft() {
                if (!this.generatedContent) return;

                try {
                    await api.patch(`/api/posts/${this.generatedContent.post_id}`, {
                        twitter_content: this.editableContent.twitter,
                        linkedin_content: this.editableContent.linkedin,
                        threads_content: this.editableContent.threads
                    }, { skipAuth: true });

                    showToast('Draft saved!', 'success');
                } catch (error) {
                    logger.error('Error saving draft:', error);
                    showToast('Failed to save draft. Please try again.', 'error');
                }
            },

            async publishPosts() {
                if (!this.generatedContent) return;

                // eslint-disable-next-line no-alert
                const confirmPublish = confirm(`Are you sure you want to publish to ${this.selectedPlatform}?`);
                if (!confirmPublish) {
                    return;
                }

                this.loading = true;
                try {
                    await api.post('/api/posts/publish', {
                        post_id: this.generatedContent.post_id,
                        platforms: [this.selectedPlatform]
                    }, { skipAuth: true });

                    showToast(`Published to ${this.selectedPlatform}!`, 'success');
                    await this.loadPosts();
                    this.selectedArticles = [];
                    this.generatedContent = null;
                    this.currentView = 'history';
                } catch (error) {
                    logger.error('Error publishing:', error);
                    showToast('Failed to publish. Please check your social media connections.', 'error');
                } finally {
                    this.loading = false;
                }
            },

            retryGeneration() {
                // Reset generation state and try again
                this.generationError = null;
                this.showGeneratingScreen = false;
                this.generatePosts();
            },

            cancelGeneration() {
                // Hide the generating screen and reset state
                this.showGeneratingScreen = false;
                this.generationError = null;
                this.platformStatus = {
                    linkedin: 'pending',
                    twitter: 'pending',
                    threads: 'pending'
                };
                this.generationStatus = {
                    linkedin: 'Waiting to start...',
                    twitter: 'Waiting to start...',
                    threads: 'Waiting to start...'
                };
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

            getStatusColor(status) {
                const colors = {
                    draft: 'bg-gray-100 text-gray-800',
                    published: 'bg-green-100 text-green-800',
                    failed: 'bg-red-100 text-red-800'
                };
                return colors[status] || 'bg-gray-100 text-gray-800';
            },

            getMaxLength(platform) {
                const limits = {
                    twitter: 280,
                    linkedin: 3000,
                    threads: 500
                };
                return limits[platform] || 280;
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

            editPost(postId) {
                // Navigate to post editor with the post ID
                window.location.href = `post-edit.html?post_id=${postId}`;
            },

            getDisplaySummary(article) {
                // For research articles, extract only the Abstract content
                if (article.category === 'research' && article.summary) {
                    const abstractMatch = article.summary.match(/Abstract:\s*([\s\S]*?)(?:\n\n|$)/);
                    if (abstractMatch && abstractMatch[1]) {
                        return abstractMatch[1].trim();
                    }
                    // Fallback: if "Abstract:" exists but pattern doesn't match, try simpler extraction
                    const abstractIndex = article.summary.indexOf('Abstract:');
                    if (abstractIndex !== -1) {
                        return article.summary.substring(abstractIndex + 9).trim();
                    }
                }
                // For non-research articles or if Abstract not found, return full summary
                return article.summary || 'No summary available';
            },

            trackArticleView(article) {
                // Track when user clicks "Read More"
                if (window.analyticsClient) {
                    window.analyticsClient.trackEvent('article_view', {
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
        logger.info('Vue app mounted successfully');
    } catch (error) {
        logger.error('Failed to mount Vue app:', error);
        console.error('Vue mount error:', error);
    }
