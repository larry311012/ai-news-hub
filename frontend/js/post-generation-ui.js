/**
 * Post Generation UI Controller
 * Handles the complete user experience for AI post generation
 *
 * Features:
 * - Immediate button feedback (<100ms)
 * - Smooth progress tracking
 * - Real-time status updates
 * - Success celebration
 * - Graceful error handling
 * - Accessibility support
 */

class PostGenerationUI {
  constructor(config = {}) {
    // Configuration
    this.config = {
      apiEndpoint: config.apiEndpoint || '/api/posts/generate',
      editorUrl: config.editorUrl || '/post-editor.html',
      profileUrl: config.profileUrl || '/profile.html',
      estimatedDuration: config.estimatedDuration || 30000, // 30 seconds
      successHoldTime: config.successHoldTime || 3000, // 3 seconds
      ...config
    };

    // State
    this.isGenerating = false;
    this.startTime = null;
    this.currentStep = 0;
    this.progressInterval = null;
    this.messageInterval = null;

    // DOM Elements
    this.button = null;
    this.overlay = null;

    // Initialize
    this.init();
  }

  /**
   * Initialize the UI controller
   */
  init() {
    this.button = document.getElementById('generateBtn');
    this.overlay = document.getElementById('loadingOverlay');

    if (!this.button) {
      console.error('Generate button not found. Expected element with id="generateBtn"');
      return;
    }

    // Attach event listeners
    this.button.addEventListener('click', () => this.handleGenerateClick());

    // Handle ESC key to cancel
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.isGenerating) {
        this.cancelGeneration();
      }
    });

  }

  /**
   * Handle generate button click
   */
  async handleGenerateClick() {
    // Prevent double-clicks
    if (this.isGenerating) {
      return;
    }

    // Validate selection
    const selectedArticles = this.getSelectedArticles();
    if (selectedArticles.length === 0) {
      this.showError({
        type: 'no_article_selected',
        message: 'Please select at least one article'
      });
      return;
    }

    // Step 1: Immediate button feedback (0ms)
    this.setButtonLoading();

    // Step 2: Show loading overlay (100ms)
    setTimeout(() => {
      this.showLoadingOverlay();
    }, 100);

    // Step 3: Make API call
    await this.generatePosts(selectedArticles);
  }

  /**
   * Set button to loading state
   */
  setButtonLoading() {
    this.button.classList.remove('btn-generate-default');
    this.button.classList.add('btn-generate-loading');
    this.button.disabled = true;

    this.button.innerHTML = `
      <span class="spinner"></span>
      <span class="btn-text">Generating Posts...</span>
      <span class="btn-subtext">Starting generation</span>
    `;
  }

  /**
   * Reset button to default state
   */
  resetButton() {
    this.button.classList.remove('btn-generate-loading');
    this.button.classList.add('btn-generate-default');
    this.button.disabled = false;

    const count = this.getSelectedArticles().length;
    const subtext = count === 1 ? '1 article selected' : `${count} articles selected`;

    this.button.innerHTML = `
      <span class="btn-icon">⚡</span>
      <span class="btn-text">Generate Posts</span>
      <span class="btn-subtext">${subtext}</span>
    `;
  }

  /**
   * Show loading overlay with progress tracking
   */
  showLoadingOverlay() {
    if (!this.overlay) {
      console.error('Loading overlay not found. Expected element with id="loadingOverlay"');
      return;
    }

    this.overlay.style.display = 'flex';
    this.startTime = Date.now();
    this.isGenerating = true;
    this.currentStep = 0;

    // Announce to screen readers
    this.announceToScreenReader('Generation started. This usually takes 10 to 30 seconds.');

    // Start progress simulation
    this.simulateProgress();

    // Start step updates
    this.updateSteps();

    // Start status messages
    this.rotateStatusMessages();

    // Focus trap
    this.trapFocus(this.overlay);
  }

  /**
   * Hide loading overlay
   */
  hideLoadingOverlay() {
    if (this.overlay) {
      this.overlay.style.display = 'none';
    }

    this.isGenerating = false;
    this.clearIntervals();
  }

  /**
   * Simulate smooth progress
   */
  simulateProgress() {
    let progress = 0;
    const targetDuration = this.config.estimatedDuration;
    const updateInterval = 100; // Update every 100ms

    this.progressInterval = setInterval(() => {
      const elapsed = Date.now() - this.startTime;
      const naturalProgress = (elapsed / targetDuration) * 100;

      // Add randomness but cap at 95% until complete
      progress = Math.min(naturalProgress + Math.random() * 5, 95);

      this.updateProgressBar(progress);
      this.updateTimeEstimate(elapsed, targetDuration);

      // Auto-stop at 95%
      if (progress >= 95) {
        clearInterval(this.progressInterval);
      }
    }, updateInterval);
  }

  /**
   * Update progress bar
   */
  updateProgressBar(percentage) {
    const fill = document.querySelector('.progress-bar-fill');
    const label = document.querySelector('.progress-percentage');

    if (fill) {
      fill.style.width = `${percentage}%`;
      fill.setAttribute('aria-valuenow', Math.round(percentage));
    }

    if (label) {
      label.textContent = `${Math.round(percentage)}%`;
    }
  }

  /**
   * Update time estimate
   */
  updateTimeEstimate(elapsed, total) {
    const remaining = Math.max(0, Math.ceil((total - elapsed) / 1000));
    const timeEl = document.getElementById('timeRemaining');

    if (timeEl) {
      timeEl.textContent = remaining;
    }
  }

  /**
   * Update step states
   */
  updateSteps() {
    const steps = [
      { time: 0, step: 'analyze', duration: 2000 },
      { time: 2000, step: 'extract', duration: 3000 },
      { time: 5000, step: 'twitter', duration: 10000 },
      { time: 15000, step: 'linkedin', duration: 7000 },
      { time: 22000, step: 'threads', duration: 8000 }
    ];

    steps.forEach(({ time, step }, index) => {
      setTimeout(() => {
        if (!this.isGenerating) return;

        // Mark current step as complete
        this.completeStep(step);

        // Announce to screen readers
        const stepName = step.charAt(0).toUpperCase() + step.slice(1);
        this.announceToScreenReader(`${stepName} complete`);

        this.currentStep = index + 1;
      }, time);
    });
  }

  /**
   * Complete a step
   */
  completeStep(stepName) {
    const stepEl = document.querySelector(`[data-step="${stepName}"]`);
    if (!stepEl) return;

    // Mark as complete
    stepEl.classList.remove('waiting', 'in-progress');
    stepEl.classList.add('complete');

    const icon = stepEl.querySelector('.step-icon');
    icon.textContent = '✅';

    // Add completion time
    const timeEl = stepEl.querySelector('.step-time');
    if (timeEl) {
      const duration = (Date.now() - this.startTime) / 1000;
      timeEl.textContent = `${duration.toFixed(1)}s`;
    }

    // Set next step as in-progress
    const nextStep = stepEl.nextElementSibling;
    if (nextStep && nextStep.classList.contains('step-item')) {
      nextStep.classList.remove('waiting');
      nextStep.classList.add('in-progress');

      const nextIcon = nextStep.querySelector('.step-icon');
      nextIcon.textContent = '🔄';
    }
  }

  /**
   * Rotate status messages
   */
  rotateStatusMessages() {
    const messages = [
      { time: 0, message: '🚀 Starting generation...', sub: 'This usually takes 10-30 seconds' },
      { time: 2000, message: '📖 Reading your article...', sub: 'Analyzing the content' },
      { time: 5000, message: '🧠 Analyzing key points...', sub: 'Extracting the most engaging insights' },
      { time: 10000, message: '✍️ Crafting engaging content...', sub: 'Tailoring posts for each platform' },
      { time: 15000, message: '🎨 Polishing your posts...', sub: 'Optimizing for maximum engagement' },
      { time: 20000, message: '✨ Almost there!', sub: 'Adding final touches' },
      { time: 25000, message: '🎉 Finalizing...', sub: 'Just a moment longer' }
    ];

    messages.forEach(({ time, message, sub }) => {
      setTimeout(() => {
        if (!this.isGenerating) return;
        this.showStatusMessage(message, sub);
      }, time);
    });
  }

  /**
   * Show status message with fade transition
   */
  showStatusMessage(message, subtext) {
    const messageEl = document.querySelector('.message-text');
    const subtextEl = document.querySelector('.message-subtext');
    const container = document.querySelector('.status-message');

    if (!container) return;

    // Fade out
    container.style.opacity = '0';

    setTimeout(() => {
      if (messageEl) messageEl.textContent = message;
      if (subtextEl) subtextEl.textContent = subtext;

      // Fade in
      container.style.opacity = '1';
    }, 150);
  }

  /**
   * Make API call to generate posts
   */
  async generatePosts(articleIds) {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        throw new Error('Not authenticated');
      }

      const response = await fetch(this.config.apiEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          },
        body: JSON.stringify({
          article_ids: articleIds
        })
      });

      if (!response.ok) {
        const error = await response.json();
        throw error;
      }

      const data = await response.json();
      this.handleSuccess(data);

    } catch (error) {
      this.handleError(error);
    }
  }

  /**
   * Handle successful generation
   */
  handleSuccess(data) {
    // Complete all remaining steps
    document.querySelectorAll('.step-item').forEach(step => {
      step.classList.remove('waiting', 'in-progress');
      step.classList.add('complete');
      const icon = step.querySelector('.step-icon');
      if (icon) icon.textContent = '✅';
    });

    // Complete progress bar
    this.updateProgressBar(100);

    // Clear intervals
    this.clearIntervals();

    // Announce to screen readers
    this.announceToScreenReader('Posts generated successfully! Redirecting to editor.');

    // Wait a moment, then show success screen
    setTimeout(() => {
      this.renderSuccessScreen(data);
    }, 500);
  }

  /**
   * Render success screen
   */
  renderSuccessScreen(data) {
    const card = document.querySelector('.loading-card');
    if (!card) return;

    card.innerHTML = `
      <h1 class="success-heading">✨ Posts Generated! ✨</h1>

      <div class="progress-container">
        <div class="progress-bar-bg">
          <div class="progress-bar-fill" style="width: 100%;" aria-valuenow="100" aria-valuemin="0" aria-valuemax="100"></div>
        </div>
      </div>

      <div class="success-posts-list">
        ${this.renderPostItems(data.posts || data)}
      </div>

      <p class="success-redirect-timer">
        Redirecting to editor in <span id="countdown">3</span> seconds...
      </p>

      <button class="success-cta" onclick="postGenUI.navigateToEditor()">
        Edit Posts Now →
      </button>
    `;

    // Start countdown
    this.startCountdown();
  }

  /**
   * Render post items
   */
  renderPostItems(posts) {
    const platforms = {
      twitter: { icon: '✅', name: 'Twitter' },
      linkedin: { icon: '✅', name: 'LinkedIn' },
      threads: { icon: '✅', name: 'Threads' }
    };

    return Object.entries(posts).map(([platform, content]) => {
      const charCount = typeof content === 'string' ? content.length : 0;
      return `
        <div class="success-post-item">
          <span class="success-post-icon">${platforms[platform]?.icon || '✅'}</span>
          <div class="success-post-details">
            <div class="success-post-platform">${platforms[platform]?.name || platform}</div>
            <div class="success-post-meta">${charCount} characters • Ready to publish</div>
          </div>
        </div>
      `;
    }).join('');
  }

  /**
   * Start countdown timer
   */
  startCountdown() {
    let count = 3;
    const countdownEl = document.getElementById('countdown');

    const timer = setInterval(() => {
      count--;
      if (countdownEl) {
        countdownEl.textContent = count;
      }

      if (count === 0) {
        clearInterval(timer);
        this.navigateToEditor();
      }
    }, 1000);
  }

  /**
   * Navigate to editor
   */
  navigateToEditor() {
    window.location.href = this.config.editorUrl;
  }

  /**
   * Handle error
   */
  handleError(error) {
    console.error('Generation error:', error);

    this.clearIntervals();
    this.isGenerating = false;

    const errorType = this.determineErrorType(error);
    const template = this.getErrorTemplate(errorType);

    // Announce to screen readers
    this.announceToScreenReader(`Error: ${template.title}`);

    const card = document.querySelector('.loading-card');
    if (!card) return;

    card.innerHTML = `
      <h1 class="error-heading">
        <span>${template.icon}</span>
        ${template.title}
      </h1>

      <p class="error-description">${template.description}</p>

      <div class="error-reason">
        <ul class="error-reason-list">
          ${template.reasons.map(r => `<li>${r}</li>`).join('')}
        </ul>
        <p class="error-reason-detail">${template.detail}</p>
      </div>

      <div class="error-steps">
        <div class="error-steps-heading">What you can do:</div>
        <ol class="error-steps-list">
          ${template.steps.map(s => `<li>${s}</li>`).join('')}
        </ol>
      </div>

      <div class="error-actions">
        ${this.renderErrorActions(template.actions)}
      </div>
    `;
  }

  /**
   * Determine error type
   */
  determineErrorType(error) {
    if (error.detail?.includes('API key') || error.message?.includes('API key')) {
      return 'no_api_key';
    }
    if (error.status === 408 || error.message?.includes('timeout')) {
      return 'generation_timeout';
    }
    if (error.status === 422 || error.detail) {
      return 'api_error';
    }
    if (!navigator.onLine || error.message?.includes('fetch')) {
      return 'network_error';
    }
    return 'api_error';
  }

  /**
   * Get error template
   */
  getErrorTemplate(type) {
    const templates = {
      no_api_key: {
        icon: '🔑',
        title: 'No API Key Found',
        description: 'We couldn\'t generate your posts because:',
        reasons: ['No API key configured'],
        detail: 'OpenAI or Anthropic API key required for generating posts',
        steps: [
          'Add your OpenAI or Anthropic API key',
          'Go to Profile → API Keys',
          'Click "Generate Posts" again'
        ],
        actions: [
          { type: 'primary', text: 'Go to API Keys', action: 'profile' },
          { type: 'tertiary', text: 'Cancel', action: 'close' }
        ]
      },

      no_article_selected: {
        icon: '📄',
        title: 'No Article Selected',
        description: 'Please select at least one article to continue.',
        reasons: ['No articles are currently selected'],
        detail: 'Select one or more articles from your feed to generate posts',
        steps: [
          'Return to your articles feed',
          'Select one or more articles',
          'Click "Generate Posts" again'
        ],
        actions: [
          { type: 'primary', text: 'Go Back', action: 'close' },
          { type: 'tertiary', text: 'Cancel', action: 'close' }
        ]
      },

      generation_timeout: {
        icon: '⏱️',
        title: 'Generation Timed Out',
        description: 'The generation took longer than expected.',
        reasons: ['Request exceeded maximum time limit (60 seconds)'],
        detail: 'This can happen with longer articles or high server load',
        steps: [
          'Try again with a shorter article',
          'Check your internet connection',
          'Contact support if this persists'
        ],
        actions: [
          { type: 'primary', text: 'Try Again', action: 'retry' },
          { type: 'tertiary', text: 'Cancel', action: 'close' }
        ]
      },

      api_error: {
        icon: '⚠️',
        title: 'Generation Failed',
        description: 'There was a problem generating your posts.',
        reasons: ['API error occurred'],
        detail: 'The AI service encountered an error. Please try again.',
        steps: [
          'Check your API key is valid',
          'Verify your API account has credits',
          'Try again in a few moments'
        ],
        actions: [
          { type: 'primary', text: 'Try Again', action: 'retry' },
          { type: 'secondary', text: 'Check API Keys', action: 'profile' },
          { type: 'tertiary', text: 'Cancel', action: 'close' }
        ]
      },

      network_error: {
        icon: '📡',
        title: 'Connection Error',
        description: 'We couldn\'t connect to the server.',
        reasons: ['Network connection lost or server unavailable'],
        detail: 'Check your internet connection and try again',
        steps: [
          'Check your internet connection',
          'Refresh the page',
          'Try again in a few moments'
        ],
        actions: [
          { type: 'primary', text: 'Try Again', action: 'retry' },
          { type: 'secondary', text: 'Refresh Page', action: 'refresh' },
          { type: 'tertiary', text: 'Cancel', action: 'close' }
        ]
      }
    };

    return templates[type] || templates.api_error;
  }

  /**
   * Render error action buttons
   */
  renderErrorActions(actions) {
    return actions.map(action => {
      const btnClass = `error-btn-${action.type}`;
      const onclick = `postGenUI.handleErrorAction('${action.action}')`;
      return `
        <button class="${btnClass}" onclick="${onclick}">
          ${action.text}
        </button>
      `;
    }).join('');
  }

  /**
   * Handle error action
   */
  handleErrorAction(action) {
    switch (action) {
      case 'profile':
        window.location.href = this.config.profileUrl;
        break;
      case 'close':
        this.hideLoadingOverlay();
        this.resetButton();
        break;
      case 'retry':
        this.hideLoadingOverlay();
        this.resetButton();
        // Trigger click again
        setTimeout(() => this.handleGenerateClick(), 100);
        break;
      case 'refresh':
        window.location.reload();
        break;
      default:
        this.hideLoadingOverlay();
        this.resetButton();
    }
  }

  /**
   * Cancel generation
   */
  cancelGeneration() {
    if (!this.isGenerating) return;

    // Announce to screen readers
    this.announceToScreenReader('Generation cancelled');

    this.hideLoadingOverlay();
    this.resetButton();
  }

  /**
   * Get selected articles
   * Override this method based on your article selection system
   */
  getSelectedArticles() {
    // Example: Get from checkboxes
    const checkboxes = document.querySelectorAll('.article-checkbox:checked');
    return Array.from(checkboxes).map(cb => cb.value);
  }

  /**
   * Clear all intervals
   */
  clearIntervals() {
    if (this.progressInterval) {
      clearInterval(this.progressInterval);
      this.progressInterval = null;
    }
    if (this.messageInterval) {
      clearInterval(this.messageInterval);
      this.messageInterval = null;
    }
  }

  /**
   * Trap focus within modal (accessibility)
   */
  trapFocus(element) {
    const focusableElements = element.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );

    const firstFocusable = focusableElements[0];
    const lastFocusable = focusableElements[focusableElements.length - 1];

    element.addEventListener('keydown', (e) => {
      if (e.key === 'Tab') {
        if (e.shiftKey && document.activeElement === firstFocusable) {
          e.preventDefault();
          lastFocusable.focus();
        } else if (!e.shiftKey && document.activeElement === lastFocusable) {
          e.preventDefault();
          firstFocusable.focus();
        }
      }
    });

    // Focus first element
    if (firstFocusable) {
      setTimeout(() => firstFocusable.focus(), 100);
    }
  }

  /**
   * Announce to screen readers
   */
  announceToScreenReader(message) {
    const announcement = document.createElement('div');
    announcement.setAttribute('role', 'status');
    announcement.setAttribute('aria-live', 'polite');
    announcement.className = 'sr-only';
    announcement.textContent = message;

    document.body.appendChild(announcement);

    setTimeout(() => {
      document.body.removeChild(announcement);
    }, 1000);
  }

  /**
   * Show error (public method)
   */
  showError(error) {
    this.handleError(error);
  }
}

// Create global instance
let postGenUI;

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    postGenUI = new PostGenerationUI();
  });
} else {
  postGenUI = new PostGenerationUI();
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
  module.exports = PostGenerationUI;
}
