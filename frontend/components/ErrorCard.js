/**
 * ErrorCard Component
 * Beautiful, actionable error messages for API failures
 *
 * Features:
 * - Clear visual hierarchy (icon → heading → explanation → actions)
 * - Contextual help with expandable sections
 * - Provider-specific guidance
 * - Auto-retry with countdown
 * - Mobile-responsive design
 */

export class ErrorCard {
    constructor(container) {
        this.container = container;
    }

    /**
     * Show error with automatic type detection and appropriate UI
     */
    show(error, context = {}) {
        const errorInfo = this.categorizeError(error, context);
        const errorHTML = this.buildErrorHTML(errorInfo);

        this.container.innerHTML = errorHTML;
        this.attachEventListeners(errorInfo);

        // Auto-retry for rate limit errors
        if (errorInfo.type === 'rate_limit' && errorInfo.retryAfter) {
            this.startRetryCountdown(errorInfo.retryAfter);
        }
    }

    /**
     * Categorize error and return structured error info
     */
    categorizeError(error, context) {
        const errorMsg = error.message || error.detail || error.toString();
        const errorLower = errorMsg.toLowerCase();

        // Quota/Credits Exhausted
        if (errorLower.includes('quota') ||
            errorLower.includes('insufficient_quota') ||
            errorLower.includes('exceeded your current quota')) {
            return {
                type: 'quota_exceeded',
                severity: 'critical',
                icon: '💳',
                heading: 'API Credits Exhausted',
                explanation: 'Your OpenAI account has run out of credits.',
                provider: context.provider || 'openai',
                actions: this.getQuotaActions(context.provider),
                helpSections: this.getQuotaHelp(context.provider)
            };
        }

        // Invalid API Key
        if (errorLower.includes('invalid api key') ||
            errorLower.includes('incorrect api key') ||
            errorLower.includes('invalid_api_key') ||
            errorLower.includes('authentication') ||
            errorLower.includes('unauthorized')) {
            return {
                type: 'invalid_key',
                severity: 'critical',
                icon: '🔑',
                heading: 'Invalid API Key',
                explanation: 'Your API key is invalid, expired, or missing required permissions.',
                provider: context.provider || 'openai',
                actions: this.getInvalidKeyActions(context.provider),
                helpSections: this.getInvalidKeyHelp(context.provider)
            };
        }

        // Rate Limiting
        if (errorLower.includes('rate limit') ||
            errorLower.includes('too many requests') ||
            errorLower.includes('429')) {
            const retryAfter = this.extractRetryAfter(error);
            return {
                type: 'rate_limit',
                severity: 'warning',
                icon: '⏱️',
                heading: 'Too Many Requests',
                explanation: 'You\'re generating posts too quickly. Please wait before trying again.',
                retryAfter: retryAfter,
                actions: this.getRateLimitActions(retryAfter),
                helpSections: this.getRateLimitHelp()
            };
        }

        // Network/Timeout
        if (errorLower.includes('timeout') ||
            errorLower.includes('network') ||
            errorLower.includes('connection')) {
            return {
                type: 'network',
                severity: 'warning',
                icon: '📡',
                heading: 'Connection Issue',
                explanation: 'Unable to reach the AI service. Please check your internet connection.',
                actions: this.getNetworkActions(),
                helpSections: this.getNetworkHelp()
            };
        }

        // Model Not Found / Deprecated
        if (errorLower.includes('model') &&
            (errorLower.includes('not found') || errorLower.includes('does not exist'))) {
            return {
                type: 'model_error',
                severity: 'warning',
                icon: '🤖',
                heading: 'AI Model Unavailable',
                explanation: 'The requested AI model is not available or has been deprecated.',
                actions: this.getModelErrorActions(),
                helpSections: this.getModelErrorHelp()
            };
        }

        // Generic API Error
        return {
            type: 'generic',
            severity: 'error',
            icon: '⚠️',
            heading: 'Generation Failed',
            explanation: errorMsg || 'An unexpected error occurred while generating your posts.',
            actions: this.getGenericActions(),
            helpSections: this.getGenericHelp()
        };
    }

    /**
     * Build HTML for error display
     */
    buildErrorHTML(errorInfo) {
        const severityColors = {
            critical: { bg: 'bg-red-900/90', border: 'border-red-600', text: 'text-red-200', button: 'bg-red-600 hover:bg-red-700' },
            warning: { bg: 'bg-amber-900/90', border: 'border-amber-600', text: 'text-amber-200', button: 'bg-amber-600 hover:bg-amber-700' },
            error: { bg: 'bg-orange-900/90', border: 'border-orange-600', text: 'text-orange-200', button: 'bg-orange-600 hover:bg-orange-700' }
        };

        const colors = severityColors[errorInfo.severity];

        return `
            <div class="error-card ${colors.bg} ${colors.border} border-2 rounded-xl p-6 shadow-2xl animate-slide-in backdrop-blur-sm"
                 role="alert"
                 aria-live="assertive">

                <!-- Header with Icon -->
                <div class="flex items-start mb-4">
                    <div class="flex-shrink-0 text-4xl mr-4" aria-hidden="true">
                        ${errorInfo.icon}
                    </div>
                    <div class="flex-1">
                        <h3 class="text-xl font-bold text-white mb-2">
                            ${errorInfo.heading}
                        </h3>
                        <p class="${colors.text} text-sm leading-relaxed">
                            ${errorInfo.explanation}
                        </p>
                    </div>
                </div>

                <!-- Quick Actions -->
                <div class="bg-black/20 rounded-lg p-4 mb-4">
                    <h4 class="text-sm font-semibold text-white mb-3">Quick Fixes:</h4>
                    <ol class="space-y-2 text-sm ${colors.text}">
                        ${errorInfo.actions.map((action, i) => `
                            <li class="flex items-start">
                                <span class="flex-shrink-0 w-6 h-6 bg-white/10 rounded-full flex items-center justify-center text-xs font-bold text-white mr-3">
                                    ${i + 1}
                                </span>
                                <div class="flex-1">
                                    ${action.html || action.text}
                                    ${action.link ? `<br><a href="${action.link}" target="_blank" class="text-blue-400 hover:text-blue-300 underline text-xs">${action.linkText || 'Learn more'} →</a>` : ''}
                                </div>
                            </li>
                        `).join('')}
                    </ol>
                </div>

                <!-- Action Buttons -->
                <div class="flex flex-wrap gap-3 mb-4">
                    ${errorInfo.retryAfter ? `
                        <button id="error-retry-btn"
                                class="${colors.button} text-white px-5 py-2.5 rounded-lg font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-gray-900 disabled:opacity-50 disabled:cursor-not-allowed"
                                disabled>
                            Retry in <span id="retry-countdown">${errorInfo.retryAfter}</span>s
                        </button>
                    ` : `
                        <button id="error-retry-btn"
                                class="${colors.button} text-white px-5 py-2.5 rounded-lg font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-gray-900">
                            Try Again
                        </button>
                    `}

                    ${errorInfo.type === 'invalid_key' || errorInfo.type === 'quota_exceeded' ? `
                        <a href="/profile.html?tab=api-keys"
                           class="bg-indigo-600 hover:bg-indigo-700 text-white px-5 py-2.5 rounded-lg font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:ring-offset-gray-900 inline-block">
                            Update API Key
                        </a>
                    ` : ''}

                    <button id="error-go-back-btn"
                            class="bg-gray-700 hover:bg-gray-600 text-white px-5 py-2.5 rounded-lg font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 focus:ring-offset-gray-900">
                        Go Back
                    </button>
                </div>

                <!-- Expandable Help Sections -->
                ${errorInfo.helpSections && errorInfo.helpSections.length > 0 ? `
                    <div class="space-y-2">
                        ${errorInfo.helpSections.map((section, i) => `
                            <details class="bg-black/20 rounded-lg overflow-hidden">
                                <summary class="px-4 py-3 cursor-pointer hover:bg-black/10 transition-colors text-sm font-medium text-white flex items-center justify-between">
                                    <span>${section.title}</span>
                                    <svg class="w-4 h-4 transform transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                                    </svg>
                                </summary>
                                <div class="px-4 py-3 text-sm ${colors.text} leading-relaxed">
                                    ${section.content}
                                </div>
                            </details>
                        `).join('')}
                    </div>
                ` : ''}

                <!-- Provider Status Link -->
                ${errorInfo.provider ? `
                    <div class="mt-4 pt-4 border-t border-white/10 text-center">
                        <a href="${this.getProviderStatusUrl(errorInfo.provider)}"
                           target="_blank"
                           class="text-xs ${colors.text} hover:text-white transition-colors inline-flex items-center">
                            Check ${this.getProviderName(errorInfo.provider)} Status
                            <svg class="w-3 h-3 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path>
                            </svg>
                        </a>
                    </div>
                ` : ''}
            </div>
        `;
    }

    /**
     * Attach event listeners
     */
    attachEventListeners(errorInfo) {
        const retryBtn = document.getElementById('error-retry-btn');
        const goBackBtn = document.getElementById('error-go-back-btn');

        if (retryBtn) {
            retryBtn.addEventListener('click', () => {
                if (window.location.href.includes('generating.html')) {
                    window.location.href = 'index.html';
                } else {
                    window.location.reload();
                }
            });
        }

        if (goBackBtn) {
            goBackBtn.addEventListener('click', () => {
                window.location.href = 'index.html';
            });
        }
    }

    /**
     * Start retry countdown timer
     */
    startRetryCountdown(seconds) {
        let remaining = seconds;
        const countdownEl = document.getElementById('retry-countdown');
        const retryBtn = document.getElementById('error-retry-btn');

        const interval = setInterval(() => {
            remaining--;
            if (countdownEl) {
                countdownEl.textContent = remaining;
            }

            if (remaining <= 0) {
                clearInterval(interval);
                if (retryBtn) {
                    retryBtn.disabled = false;
                    retryBtn.innerHTML = 'Retry Now';
                }
            }
        }, 1000);
    }

    /**
     * Extract retry-after value from error
     */
    extractRetryAfter(error) {
        // Check for Retry-After header or value in error
        if (error.headers && error.headers['retry-after']) {
            return parseInt(error.headers['retry-after']);
        }

        const errorMsg = error.message || error.toString();
        const match = errorMsg.match(/retry.*?(\d+)\s*second/i);
        if (match) {
            return parseInt(match[1]);
        }

        // Default to 30 seconds
        return 30;
    }

    // ========================================================================
    // ACTION DEFINITIONS
    // ========================================================================

    getQuotaActions(provider) {
        if (provider === 'anthropic') {
            return [
                {
                    text: 'Check your Claude console for usage limits',
                    link: 'https://console.anthropic.com/settings/limits',
                    linkText: 'Open Claude Console'
                },
                {
                    text: 'Add billing information to increase quota',
                    link: 'https://console.anthropic.com/settings/billing',
                    linkText: 'Add Billing'
                },
                {
                    text: 'Switch to OpenAI temporarily (if you have a key)',
                    link: '/profile.html?tab=api-keys',
                    linkText: 'Update API Keys'
                }
            ];
        }

        // OpenAI (default)
        return [
            {
                text: 'Add billing information to your OpenAI account',
                link: 'https://platform.openai.com/account/billing',
                linkText: 'Add Billing'
            },
            {
                text: 'Switch to Anthropic (Claude) if you have credits',
                link: '/profile.html?tab=api-keys',
                linkText: 'Update API Keys'
            },
            {
                text: 'Wait for your free tier credits to reset (if applicable)'
            }
        ];
    }

    getInvalidKeyActions(provider) {
        const providerName = this.getProviderName(provider);
        const keyUrl = provider === 'anthropic'
            ? 'https://console.anthropic.com/settings/keys'
            : 'https://platform.openai.com/api-keys';

        return [
            {
                text: `Generate a new API key from ${providerName}`,
                link: keyUrl,
                linkText: `Open ${providerName} Dashboard`
            },
            {
                text: 'Update your key in Profile → API Keys',
                link: '/profile.html?tab=api-keys',
                linkText: 'Update Now'
            },
            {
                text: 'Ensure the key has correct permissions (full API access)'
            }
        ];
    }

    getRateLimitActions(retryAfter) {
        return [
            {
                text: `Wait ${retryAfter} seconds before generating again`
            },
            {
                text: 'Consider upgrading your API plan for higher rate limits'
            },
            {
                text: 'Generate fewer platforms at once to reduce load'
            }
        ];
    }

    getNetworkActions() {
        return [
            {
                text: 'Check your internet connection'
            },
            {
                text: 'Refresh the page and try again'
            },
            {
                text: 'Disable VPN or proxy if you\'re using one'
            }
        ];
    }

    getModelErrorActions() {
        return [
            {
                text: 'The AI model may be temporarily unavailable'
            },
            {
                text: 'Try switching to a different AI provider',
                link: '/profile.html?tab=api-keys',
                linkText: 'Update Provider'
            },
            {
                text: 'Contact support if the issue persists'
            }
        ];
    }

    getGenericActions() {
        return [
            {
                text: 'Refresh the page and try again'
            },
            {
                text: 'Check your API key configuration',
                link: '/profile.html?tab=api-keys',
                linkText: 'View API Keys'
            },
            {
                text: 'Contact support if the problem continues'
            }
        ];
    }

    // ========================================================================
    // HELP SECTIONS
    // ========================================================================

    getQuotaHelp(provider) {
        if (provider === 'anthropic') {
            return [
                {
                    title: '💡 Why did this happen?',
                    content: `You've used all available credits on your Claude API account. This could be due to:
                        <ul class="list-disc ml-5 mt-2 space-y-1">
                            <li>Exceeding your monthly credit limit</li>
                            <li>No billing method configured</li>
                            <li>Generating many posts in a short time</li>
                        </ul>`
                },
                {
                    title: '🔧 How to fix permanently',
                    content: `To avoid this in the future:
                        <ul class="list-disc ml-5 mt-2 space-y-1">
                            <li>Add a payment method to your Claude account for pay-as-you-go billing</li>
                            <li>Monitor your usage in the Claude console</li>
                            <li>Set up usage alerts for your account</li>
                        </ul>`
                }
            ];
        }

        return [
            {
                title: '💡 Why did this happen?',
                content: `You've exceeded your OpenAI quota. Common causes:
                    <ul class="list-disc ml-5 mt-2 space-y-1">
                        <li>No billing method on file (new accounts get limited free credits)</li>
                        <li>Reached your monthly spending limit</li>
                        <li>Used all pre-paid credits</li>
                    </ul>`
            },
            {
                title: '🔧 How to fix permanently',
                content: `To avoid this in the future:
                    <ul class="list-disc ml-5 mt-2 space-y-1">
                        <li>Add a payment method: <a href="https://platform.openai.com/account/billing" target="_blank" class="text-blue-400 hover:text-blue-300 underline">OpenAI Billing</a></li>
                        <li>Set usage limits in your OpenAI dashboard</li>
                        <li>Monitor your API usage regularly</li>
                    </ul>`
            },
            {
                title: '🎯 Pro Tip',
                content: 'Claude (Anthropic) often has different pricing and limits. Consider having both providers configured for redundancy.'
            }
        ];
    }

    getInvalidKeyHelp(provider) {
        return [
            {
                title: '💡 Why did this happen?',
                content: `Your API key is not working. Possible reasons:
                    <ul class="list-disc ml-5 mt-2 space-y-1">
                        <li>Key was deleted or regenerated</li>
                        <li>Key doesn't have necessary permissions</li>
                        <li>Typo when entering the key</li>
                        <li>Account has been suspended</li>
                    </ul>`
            },
            {
                title: '🔑 How to get a valid key',
                content: `Follow these steps:
                    <ol class="list-decimal ml-5 mt-2 space-y-1">
                        <li>Go to ${provider === 'anthropic' ? 'Claude Console' : 'OpenAI Dashboard'}</li>
                        <li>Navigate to API Keys section</li>
                        <li>Create a new key (name it something like "AI Post App")</li>
                        <li>Copy the key immediately (you won't see it again!)</li>
                        <li>Paste it in Profile → API Keys in this app</li>
                    </ol>`
            }
        ];
    }

    getRateLimitHelp() {
        return [
            {
                title: '💡 Why did this happen?',
                content: `API providers limit how many requests you can make per minute to prevent abuse and ensure service quality. You've hit this limit.`
            },
            {
                title: '⏰ How to avoid this',
                content: `Tips to stay under rate limits:
                    <ul class="list-disc ml-5 mt-2 space-y-1">
                        <li>Generate posts for fewer platforms at once</li>
                        <li>Wait 30-60 seconds between generation attempts</li>
                        <li>Upgrade to a higher API tier for increased limits</li>
                    </ul>`
            }
        ];
    }

    getNetworkHelp() {
        return [
            {
                title: '💡 Why did this happen?',
                content: 'The app couldn\'t connect to the AI service. This is usually a temporary network issue on your end or the provider\'s servers.'
            },
            {
                title: '🔧 Troubleshooting steps',
                content: `Try these solutions:
                    <ol class="list-decimal ml-5 mt-2 space-y-1">
                        <li>Check if you can access other websites</li>
                        <li>Disable VPN/proxy temporarily</li>
                        <li>Try a different network (mobile hotspot)</li>
                        <li>Check provider status page for outages</li>
                    </ol>`
            }
        ];
    }

    getModelErrorHelp() {
        return [
            {
                title: '💡 Why did this happen?',
                content: 'The AI model you\'re trying to use is unavailable. Models can be deprecated, temporarily down, or restricted to certain accounts.'
            }
        ];
    }

    getGenericHelp() {
        return [
            {
                title: '💡 What to try',
                content: `General troubleshooting:
                    <ul class="list-disc ml-5 mt-2 space-y-1">
                        <li>Refresh the page</li>
                        <li>Clear your browser cache</li>
                        <li>Check API key configuration</li>
                        <li>Try a different browser</li>
                    </ul>`
            }
        ];
    }

    // ========================================================================
    // HELPER METHODS
    // ========================================================================

    getProviderName(provider) {
        const names = {
            'openai': 'OpenAI',
            'anthropic': 'Claude'
        };
        return names[provider] || provider;
    }

    getProviderStatusUrl(provider) {
        const urls = {
            'openai': 'https://status.openai.com/',
            'anthropic': 'https://status.anthropic.com/'
        };
        return urls[provider] || 'https://status.openai.com/';
    }
}

// Export for use in other modules
export default ErrorCard;
