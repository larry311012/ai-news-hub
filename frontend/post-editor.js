import { showToast } from './utils/toast.js';
import { createApp } from 'vue'
import axios from 'axios'
import '/src/style.css'

const API_BASE_URL = `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api`;

const app = createApp({
    data() {
        return {
            // Article data
            article: {
                id: 1,
                title: 'The Future of AI: Transforming Industries',
                category: 'news',
                source: 'TechCrunch',
                published: '2025-01-15T10:00:00Z',
                link: 'https://example.com/article'
            },

            // Content for each platform
            content: {
                twitter: '',
                linkedin: '',
                threads: ''
            },

            // Platform configuration
            platforms: [
                {
                    id: 'twitter',
                    name: 'Twitter',
                    icon: '<svg fill="currentColor" class="text-sky-500" viewBox="0 0 24 24"><path d="M23.953 4.57a10 10 0 01-2.825.775 4.958 4.958 0 002.163-2.723c-.951.555-2.005.959-3.127 1.184a4.92 4.92 0 00-8.384 4.482C7.69 8.095 4.067 6.13 1.64 3.162a4.822 4.822 0 00-.666 2.475c0 1.71.87 3.213 2.188 4.096a4.904 4.904 0 01-2.228-.616v.06a4.923 4.923 0 003.946 4.827 4.996 4.996 0 01-2.212.085 4.936 4.936 0 004.604 3.417 9.867 9.867 0 01-6.102 2.105c-.39 0-.779-.023-1.17-.067a13.995 13.995 0 007.557 2.209c9.053 0 13.998-7.496 13.998-13.985 0-.21 0-.42-.015-.63A9.935 9.935 0 0024 4.59z"/></svg>',
                    limit: 280
                },
                {
                    id: 'linkedin',
                    name: 'LinkedIn',
                    icon: '<svg fill="currentColor" class="text-blue-600" viewBox="0 0 24 24"><path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z"/></svg>',
                    limit: 3000
                },
                {
                    id: 'threads',
                    name: 'Threads',
                    icon: '<svg fill="currentColor" class="text-purple-600" viewBox="0 0 24 24"><path d="M12.186 24h-.007c-3.581-.024-6.334-1.205-8.184-3.509C2.35 18.44 1.5 15.586 1.472 12.01v-.017c.03-3.579.879-6.43 2.525-8.482C5.845 1.205 8.6.024 12.18 0h.014c2.746.02 5.043.725 6.826 2.098 1.677 1.29 2.858 3.13 3.509 5.467l-2.04.569c-1.104-3.96-3.898-5.984-8.304-6.015-2.91.022-5.11.936-6.54 2.717C4.307 6.504 3.616 8.914 3.589 12c.027 3.086.718 5.496 2.057 7.164 1.43 1.781 3.631 2.695 6.54 2.717 2.623-.02 4.358-.631 5.8-2.045 1.647-1.613 1.618-3.593 1.09-4.798-.31-.71-.873-1.3-1.634-1.75-.192 1.352-.622 2.446-1.284 3.272-.886 1.102-2.14 1.704-3.73 1.79-1.202.065-2.361-.218-3.259-.801-1.063-.689-1.685-1.74-1.752-2.964-.065-1.19.408-2.285 1.33-3.082.88-.76 2.119-1.207 3.583-1.291a13.853 13.853 0 013.02.142l-.126 1.974a11.881 11.881 0 00-2.58-.123c-1.018.056-1.84.344-2.446.855-.583.493-.87 1.12-.834 1.814.036.683.388 1.217.99 1.502.539.255 1.277.354 2.101.28 1.15-.093 2.059-.535 2.702-1.315.646-.784.972-1.858.972-3.197V8.033c0-.458-.006-.916-.02-1.373l2.04-.057c.013.457.02.915.02 1.373v1.78c.598-.421 1.3-.758 2.092-.998 1.004-.304 2.085-.457 3.212-.457l.126 1.99c-.905 0-1.766.123-2.562.366-.796.243-1.47.6-2.004 1.062v1.304c.54.694.97 1.49 1.28 2.369.726 2.057.746 4.753-1.44 6.993-1.817 1.869-4.138 2.82-7.106 2.848z"/></svg>',
                    limit: 500
                }
            ],

            // UI state
            activePlatform: 'twitter',
            selectedPlatforms: [],

            // Platform connections
            platformConnections: {
                twitter: null, // { username: 'johndoe', status: 'connected' }
                linkedin: null,
                threads: null
            },

            // Saving state
            saving: false,
            autoSaving: false,
            lastSaved: null,
            autoSaveTimer: null,

            // Publishing state
            showPublishModal: false,
            publishing: false,
            publishProgress: {},
            showSuccessModal: false,
            showErrorModal: false,
            errorMessage: '',
            publishErrors: {},
            publishedLinks: {},

            // Estimated reach (mock data)
            estimatedReach: {
                twitter: '2.4K',
                linkedin: '1.8K',
                threads: '950'
            }
        };
    },

    computed: {
        canPublish() {
            return this.selectedPlatforms.length > 0 &&
                   this.selectedPlatforms.some(p => this.getConnectionStatus(p) === 'connected');
        }
    },

    mounted() {
        // Load saved content from localStorage or API
        this.loadDraft();

        // Check platform connections
        this.checkPlatformConnections();

        // Setup auto-save
        this.setupAutoSave();

        // Load sample content for demo
        this.loadSampleContent();
    },

    beforeUnmount() {
        // Clear auto-save timer
        if (this.autoSaveTimer) {
            clearInterval(this.autoSaveTimer);
        }
    },

    methods: {
        // Navigation
        goBack() {
            if (confirm('Are you sure you want to leave? Unsaved changes will be lost.')) {
                window.location.href = 'index.html';
            }
        },

        // Platform methods
        getPlatformName(platformId) {
            const platform = this.platforms.find(p => p.id === platformId);
            return platform ? platform.name : platformId;
        },

        getPlatformLimit(platformId) {
            const platform = this.platforms.find(p => p.id === platformId);
            return platform ? platform.limit : 280;
        },

        getContentLength(platformId) {
            return this.content[platformId]?.length || 0;
        },

        getCharCountClass(platformId) {
            const length = this.getContentLength(platformId);
            const limit = this.getPlatformLimit(platformId);
            const percentage = (length / limit) * 100;

            if (percentage >= 100) return 'char-counter-danger font-semibold';
            if (percentage >= 90) return 'char-counter-warning font-semibold';
            return 'text-gray-500';
        },

        getPlaceholder(platformId) {
            const placeholders = {
                twitter: 'Write your tweet here... Use hashtags and mentions to increase engagement.',
                linkedin: 'Share your professional insights on LinkedIn...',
                threads: 'Create an engaging Threads post...'
            };
            return placeholders[platformId] || 'Write your post here...';
        },

        // Connection status
        getConnectionStatus(platformId) {
            const connection = this.platformConnections[platformId];
            if (!connection) return 'not_connected';
            if (connection.error) return 'error';
            return 'connected';
        },

        getConnectionWarningTitle(platformId) {
            const status = this.getConnectionStatus(platformId);
            if (status === 'error') return 'Connection Error';
            return 'Platform Not Connected';
        },

        getConnectionWarningMessage(platformId) {
            const status = this.getConnectionStatus(platformId);
            const platformName = this.getPlatformName(platformId);

            if (status === 'error') {
                return `There was an error connecting to ${platformName}. Please reconnect your account.`;
            }
            return `Connect your ${platformName} account to publish posts directly from here.`;
        },

        async checkPlatformConnections() {
            // Mock connection check - replace with actual API call
            // In real implementation, this would call the backend to check OAuth status

            // Simulating some connections
            this.platformConnections.twitter = {
                username: 'johndoe',
                status: 'connected'
            };

            // Auto-select connected platforms
            this.selectedPlatforms = Object.keys(this.platformConnections)
                .filter(platform => this.platformConnections[platform]);
        },

        async connectPlatform(platformId) {
            // Redirect to OAuth flow or open connection wizard
            showToast(`Redirecting to ${this.getPlatformName(platformId)} OAuth flow...`, 'warning');

            // In real implementation:
            // window.location.href = `${API_BASE_URL}/oauth/${platformId}/authorize`;
        },

        // Content management
        handleContentChange() {
            // Trigger auto-save
            this.triggerAutoSave();
        },

        setupAutoSave() {
            // Auto-save every 30 seconds if there are changes
            this.autoSaveTimer = setInterval(() => {
                if (this.hasUnsavedChanges()) {
                    this.performAutoSave();
                }
            }, 30000);
        },

        hasUnsavedChanges() {
            // Check if content has changed since last save
            const savedContent = localStorage.getItem('draft_content');
            const currentContent = JSON.stringify(this.content);
            return savedContent !== currentContent;
        },

        triggerAutoSave() {
            // Debounced auto-save
            if (this.autoSaveTimer) {
                clearTimeout(this.autoSaveTimer);
            }

            this.autoSaveTimer = setTimeout(() => {
                this.performAutoSave();
            }, 2000);
        },

        async performAutoSave() {
            this.autoSaving = true;

            try {
                // Save to localStorage
                localStorage.setItem('draft_content', JSON.stringify(this.content));

                // In real implementation, save to backend
                // await axios.post(`${API_BASE_URL}/posts/draft`, this.content);

                this.lastSaved = new Date();
            } catch (error) {
                console.error('Auto-save failed:', error);
            } finally {
                this.autoSaving = false;
            }
        },

        async saveDraft() {
            this.saving = true;

            try {
                // Save to backend
                // await axios.post(`${API_BASE_URL}/posts/draft`, {
                //     article_id: this.article.id,
                //     content: this.content
                // });

                localStorage.setItem('draft_content', JSON.stringify(this.content));
                this.lastSaved = new Date();

                showToast('Draft saved successfully!', 'success');
            } catch (error) {
                console.error('Save draft failed:', error);
                showToast('Failed to save draft. Please try again.', 'error');
            } finally {
                this.saving = false;
            }
        },

        loadDraft() {
            // Load from localStorage
            const savedContent = localStorage.getItem('draft_content');
            if (savedContent) {
                try {
                    this.content = JSON.parse(savedContent);
                } catch (error) {
                    console.error('Failed to load draft:', error);
                }
            }
        },

        loadSampleContent() {
            // Load sample generated content for demo
            if (!this.content.twitter) {
                this.content.twitter = `🚀 The future of AI is here! New breakthrough in machine learning transforms how we work.\n\nKey highlights:\n✅ 10x faster processing\n✅ 90% accuracy improvement\n✅ Real-world applications\n\nRead more: [link]\n\n#AI #MachineLearning #Tech`;
            }

            if (!this.content.linkedin) {
                this.content.linkedin = `The Future of AI: A Game-Changer for Industries\n\nArtificial Intelligence continues to reshape our world in unprecedented ways. Recent breakthroughs in machine learning are not just incremental improvements—they represent fundamental shifts in what's possible.\n\n🔍 Key Insights:\n\n• Processing speeds have increased by 10x, enabling real-time analysis of massive datasets\n• Accuracy rates now exceed 90%, making AI reliable for critical applications\n• New applications are emerging across healthcare, finance, and manufacturing\n\nWhat does this mean for professionals? The ability to augment human decision-making with AI insights will become a core competency across all industries.\n\nThe question isn't whether AI will transform your field—it's how quickly you'll adapt to leverage these powerful new tools.\n\nWhat are your thoughts on AI's impact in your industry? Share in the comments below.\n\n#ArtificialIntelligence #Innovation #FutureOfWork #Technology`;
            }

            if (!this.content.threads) {
                this.content.threads = `AI is transforming industries faster than ever! 🚀\n\nNew breakthroughs are achieving:\n• 10x processing speed\n• 90% accuracy rates\n• Real-world impact across sectors\n\nThe future is being built today. Are you ready?\n\n#AI #Innovation`;
            }
        },

        // Editor tools
        formatBold() {
            // Add bold formatting (platform-specific)
            const platform = this.activePlatform;
            this.content[platform] += '**bold text**';
        },

        addHashtag() {
            const platform = this.activePlatform;
            this.content[platform] += ' #';
        },

        addEmoji() {
            const platform = this.activePlatform;
            this.content[platform] += ' 🚀';
        },

        async regenerateContent(platformId) {
            if (!confirm(`Regenerate content for ${this.getPlatformName(platformId)}? This will replace your current content.`)) {
                return;
            }

            // Call AI to regenerate
            showToast('Regenerating content... (calling OpenAI API)', 'info');

            // In real implementation:
            // const response = await axios.post(`${API_BASE_URL}/posts/regenerate`, {
            //     platform: platformId,
            //     article_id: this.article.id
            // });
            // this.content[platformId] = response.data.content;
        },

        // Publishing
        openPublishModal() {
            if (this.selectedPlatforms.length === 0) {
                showToast('Please select at least one platform to publish to.', 'warning');
                return;
            }
            this.showPublishModal = true;
        },

        closePublishModal() {
            this.showPublishModal = false;
        },

        async confirmPublish() {
            this.publishing = true;
            this.showPublishModal = false;

            // Initialize progress tracking
            this.publishProgress = {};
            this.publishErrors = {};
            this.publishedLinks = {};

            this.selectedPlatforms.forEach(platform => {
                this.publishProgress[platform] = 'publishing';
            });

            try {
                // Publish to each platform
                for (const platform of this.selectedPlatforms) {
                    try {
                        await this.publishToPlatform(platform);
                        this.publishProgress[platform] = 'success';

                        // Mock published link
                        this.publishedLinks[platform] = `https://${platform}.com/post/123456`;
                    } catch (error) {
                        console.error(`Failed to publish to ${platform}:`, error);
                        this.publishProgress[platform] = 'error';
                        this.publishErrors[platform] = error.message || 'Unknown error';
                    }
                }

                // Check if all succeeded
                const allSucceeded = this.selectedPlatforms.every(
                    p => this.publishProgress[p] === 'success'
                );

                if (allSucceeded) {
                    this.showSuccessModal = true;
                } else {
                    this.errorMessage = 'Some platforms failed to publish. Please try again.';
                    this.showErrorModal = true;
                }
            } catch (error) {
                console.error('Publishing error:', error);
                this.errorMessage = error.message || 'Failed to publish posts. Please try again.';
                this.showErrorModal = true;
            } finally {
                this.publishing = false;
            }
        },

        async publishToPlatform(platformId) {
            // Simulate API call delay
            await new Promise(resolve => setTimeout(resolve, 1000 + Math.random() * 2000));

            // Mock success rate (90% success for demo)
            if (Math.random() < 0.1) {
                throw new Error('API rate limit exceeded');
            }

            // In real implementation:
            // const response = await axios.post(`${API_BASE_URL}/posts/publish`, {
            //     platform: platformId,
            //     content: this.content[platformId],
            //     article_id: this.article.id
            // });
            // return response.data;
        },

        retryPublish() {
            this.closeErrorModal();
            this.confirmPublish();
        },

        closeSuccessModal() {
            this.showSuccessModal = false;
            // Optionally redirect to history page
            // window.location.href = 'index.html?view=history';
        },

        closeErrorModal() {
            this.showErrorModal = false;
        },

        getPublishedPostLink(platformId) {
            return this.publishedLinks[platformId] || '#';
        },

        // Utilities
        formatDate(dateString) {
            const date = new Date(dateString);
            return date.toLocaleDateString('en-US', {
                month: 'long',
                day: 'numeric',
                year: 'numeric'
            });
        },

        formatTimeSince(date) {
            const seconds = Math.floor((new Date() - date) / 1000);

            if (seconds < 60) return 'just now';
            if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
            if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
            return `${Math.floor(seconds / 86400)}d ago`;
        }
    }
});

app.mount('#post-editor-app');
