/**
 * AddSourceModal Component Tests
 *
 * Test suite for the RSS Feed Add Source Modal component
 * Tests all 3 wizard steps, API integration, and error handling
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount } from '@vue/test-utils';
import AddSourceModal from './AddSourceModal.vue';

describe('AddSourceModal', () => {
  let wrapper;

  beforeEach(() => {
    // Reset localStorage
    localStorage.clear();

    // Mock fetch
    global.fetch = vi.fn();
  });

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount();
    }
  });

  describe('Step 1: Method Selection', () => {
    it('renders step 1 on mount', () => {
      wrapper = mount(AddSourceModal, {
        props: { show: true }
      });

      expect(wrapper.find('.add-source-step-1').exists()).toBe(false); // No class, just v-if
      expect(wrapper.text()).toContain('How would you like to add a source?');
    });

    it('allows selecting website URL method', async () => {
      wrapper = mount(AddSourceModal, {
        props: { show: true }
      });

      const urlOption = wrapper.findAll('.option-card')[0];
      await urlOption.trigger('click');

      expect(wrapper.vm.selectedMethod).toBe('url');
    });

    it('allows selecting RSS method', async () => {
      wrapper = mount(AddSourceModal, {
        props: { show: true }
      });

      const rssOption = wrapper.findAll('.option-card')[1];
      await rssOption.trigger('click');

      expect(wrapper.vm.selectedMethod).toBe('rss');
    });

    it('disables continue button when no method selected', () => {
      wrapper = mount(AddSourceModal, {
        props: { show: true }
      });

      const continueBtn = wrapper.findAll('button').find(btn =>
        btn.text().includes('Continue')
      );

      expect(continueBtn.attributes('disabled')).toBeDefined();
    });

    it('enables continue button when method selected', async () => {
      wrapper = mount(AddSourceModal, {
        props: { show: true }
      });

      await wrapper.vm.$nextTick();
      wrapper.vm.selectedMethod = 'url';
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.canProceedToNextStep).toBe(true);
    });
  });

  describe('Step 2: Discovery (Website URL method)', () => {
    beforeEach(async () => {
      wrapper = mount(AddSourceModal, {
        props: { show: true }
      });
      wrapper.vm.selectedMethod = 'url';
      wrapper.vm.currentStep = 2;
      await wrapper.vm.$nextTick();
    });

    it('displays website URL input field', () => {
      expect(wrapper.find('#website-url').exists()).toBe(true);
    });

    it('calls discovery API on blur', async () => {
      const mockFeeds = [
        {
          url: 'https://techcrunch.com/feed/',
          title: 'TechCrunch',
          type: 'rss',
          description: 'Tech news',
          item_count: 25
        }
      ];

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ discovered_feeds: mockFeeds })
      });

      localStorage.setItem('auth_token', 'test-token');
      wrapper.vm.websiteUrl = 'https://techcrunch.com';

      await wrapper.vm.handleDiscovery();

      expect(global.fetch).toHaveBeenCalledWith(
        '/api/user-feeds/discover',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Authorization': 'Bearer test-token'
          })
        })
      );

      expect(wrapper.vm.discoveredFeeds).toEqual(mockFeeds);
    });

    it('displays discovered feeds', async () => {
      wrapper.vm.discoveredFeeds = [
        {
          url: 'https://techcrunch.com/feed/',
          title: 'TechCrunch',
          type: 'rss',
          description: 'Tech news',
          item_count: 25
        }
      ];
      wrapper.vm.discovering = false;
      await wrapper.vm.$nextTick();

      expect(wrapper.text()).toContain('Found 1 feed(s)');
      expect(wrapper.text()).toContain('TechCrunch');
    });

    it('auto-selects feed when only one found', async () => {
      const mockFeeds = [
        {
          url: 'https://techcrunch.com/feed/',
          title: 'TechCrunch',
          type: 'rss',
          description: 'Tech news',
          item_count: 25
        }
      ];

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ discovered_feeds: mockFeeds })
      });

      localStorage.setItem('auth_token', 'test-token');
      wrapper.vm.websiteUrl = 'https://techcrunch.com';

      await wrapper.vm.handleDiscovery();

      expect(wrapper.vm.selectedFeed).toEqual(mockFeeds[0]);
    });

    it('shows "no feeds found" warning', async () => {
      wrapper.vm.discoveredFeeds = [];
      wrapper.vm.attemptedDiscovery = true;
      wrapper.vm.discovering = false;
      await wrapper.vm.$nextTick();

      expect(wrapper.text()).toContain('No feeds found');
      expect(wrapper.text()).toContain('Switch to direct URL entry');
    });

    it('switches to RSS method when button clicked', async () => {
      wrapper.vm.discoveredFeeds = [];
      wrapper.vm.attemptedDiscovery = true;
      wrapper.vm.discovering = false;
      await wrapper.vm.$nextTick();

      const switchBtn = wrapper.find('button').filter(btn =>
        btn.text().includes('Switch to direct URL entry')
      )[0];

      if (switchBtn) {
        await switchBtn.trigger('click');
        expect(wrapper.vm.selectedMethod).toBe('rss');
        expect(wrapper.vm.currentStep).toBe(1);
      }
    });
  });

  describe('Step 2: Validation (RSS method)', () => {
    beforeEach(async () => {
      wrapper = mount(AddSourceModal, {
        props: { show: true }
      });
      wrapper.vm.selectedMethod = 'rss';
      wrapper.vm.currentStep = 2;
      await wrapper.vm.$nextTick();
    });

    it('displays feed URL input field', () => {
      expect(wrapper.find('#feed-url').exists()).toBe(true);
    });

    it('calls validation API on blur', async () => {
      const mockValidation = {
        is_valid: true,
        feed_metadata: {
          title: 'TechCrunch',
          description: 'Tech news',
          type: 'rss',
          item_count: 25
        }
      };

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => mockValidation
      });

      localStorage.setItem('auth_token', 'test-token');
      wrapper.vm.feedUrl = 'https://techcrunch.com/feed/';

      await wrapper.vm.handleValidation();

      expect(global.fetch).toHaveBeenCalledWith(
        '/api/user-feeds/validate',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Authorization': 'Bearer test-token'
          })
        })
      );

      expect(wrapper.vm.validationResult).toEqual(mockValidation);
    });

    it('shows success state when validation passes', async () => {
      wrapper.vm.validationResult = {
        is_valid: true,
        feed_metadata: {
          title: 'TechCrunch',
          item_count: 25
        }
      };
      wrapper.vm.validating = false;
      await wrapper.vm.$nextTick();

      expect(wrapper.text()).toContain('Feed validated successfully!');
      expect(wrapper.text()).toContain('TechCrunch');
    });

    it('shows error state when validation fails', async () => {
      wrapper.vm.validationResult = null;
      wrapper.vm.validationError = 'Feed not found (404)';
      wrapper.vm.validating = false;
      await wrapper.vm.$nextTick();

      expect(wrapper.text()).toContain('Couldn\'t validate feed');
      expect(wrapper.text()).toContain('Feed not found (404)');
    });

    it('allows retry on validation failure', async () => {
      wrapper.vm.validationError = 'Some error';
      wrapper.vm.validating = false;
      await wrapper.vm.$nextTick();

      const retryBtn = wrapper.findAll('button').find(btn =>
        btn.text().includes('Try again')
      );

      if (retryBtn) {
        global.fetch = vi.fn().mockResolvedValue({
          ok: true,
          json: async () => ({ is_valid: true, feed_metadata: {} })
        });

        localStorage.setItem('auth_token', 'test-token');
        wrapper.vm.feedUrl = 'https://example.com/feed';

        await retryBtn.trigger('click');

        expect(wrapper.vm.validationError).toBeNull();
      }
    });
  });

  describe('Step 3: Configure & Add', () => {
    beforeEach(async () => {
      wrapper = mount(AddSourceModal, {
        props: { show: true }
      });
      wrapper.vm.selectedMethod = 'url';
      wrapper.vm.selectedFeed = {
        url: 'https://techcrunch.com/feed/',
        title: 'TechCrunch',
        type: 'rss',
        description: 'Tech news'
      };
      wrapper.vm.currentStep = 3;
      await wrapper.vm.$nextTick();
    });

    it('pre-fills feed name from auto-detected name', () => {
      expect(wrapper.vm.feedName).toBe('TechCrunch');
    });

    it('displays feed name input', () => {
      expect(wrapper.find('#feed-name').exists()).toBe(true);
    });

    it('displays update frequency dropdown', () => {
      expect(wrapper.find('#update-frequency').exists()).toBe(true);
    });

    it('defaults update frequency to 1 hour', () => {
      expect(wrapper.vm.updateFrequency).toBe(3600);
    });

    it('calls add feed API when submitted', async () => {
      const mockResponse = {
        id: 1,
        feed: {
          id: 1,
          feed_name: 'TechCrunch',
          feed_url: 'https://techcrunch.com/feed/'
        }
      };

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => mockResponse
      });

      localStorage.setItem('auth_token', 'test-token');
      wrapper.vm.feedName = 'TechCrunch';

      await wrapper.vm.handleAddFeed();

      expect(global.fetch).toHaveBeenCalledWith(
        '/api/user-feeds',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Authorization': 'Bearer test-token'
          }),
          body: expect.stringContaining('TechCrunch')
        })
      );
    });

    it('emits added event on success', async () => {
      const mockResponse = {
        id: 1,
        feed: { id: 1, feed_name: 'TechCrunch' }
      };

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => mockResponse
      });

      localStorage.setItem('auth_token', 'test-token');
      wrapper.vm.feedName = 'TechCrunch';

      await wrapper.vm.handleAddFeed();

      expect(wrapper.emitted('added')).toBeTruthy();
      expect(wrapper.emitted('added')[0][0]).toEqual(mockResponse.feed);
    });

    it('handles add feed error', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        json: async () => ({ detail: 'Feed already exists' })
      });

      localStorage.setItem('auth_token', 'test-token');
      wrapper.vm.feedName = 'TechCrunch';

      await wrapper.vm.handleAddFeed();

      // Should not emit added event
      expect(wrapper.emitted('added')).toBeFalsy();
    });
  });

  describe('Modal Controls', () => {
    it('emits close event when close button clicked', async () => {
      wrapper = mount(AddSourceModal, {
        props: { show: true }
      });

      const closeBtn = wrapper.find('button[aria-label="Close modal"]');
      await closeBtn.trigger('click');

      expect(wrapper.emitted('close')).toBeTruthy();
    });

    it('closes modal on ESC key', async () => {
      wrapper = mount(AddSourceModal, {
        props: { show: true }
      });

      await wrapper.vm.handleEscape({ key: 'Escape' });

      expect(wrapper.emitted('close')).toBeTruthy();
    });

    it('prevents closing during async operations', async () => {
      wrapper = mount(AddSourceModal, {
        props: { show: true }
      });

      wrapper.vm.discovering = true;
      await wrapper.vm.handleClose();

      expect(wrapper.emitted('close')).toBeFalsy();
    });

    it('resets state when modal closes', async () => {
      wrapper = mount(AddSourceModal, {
        props: { show: true }
      });

      wrapper.vm.selectedMethod = 'url';
      wrapper.vm.websiteUrl = 'https://example.com';
      wrapper.vm.currentStep = 2;

      wrapper.vm.resetModal();

      expect(wrapper.vm.currentStep).toBe(1);
      expect(wrapper.vm.selectedMethod).toBeNull();
      expect(wrapper.vm.websiteUrl).toBe('');
    });
  });

  describe('Navigation', () => {
    beforeEach(() => {
      wrapper = mount(AddSourceModal, {
        props: { show: true }
      });
    });

    it('navigates to step 2 when continue clicked', async () => {
      wrapper.vm.selectedMethod = 'url';
      await wrapper.vm.nextStep();

      expect(wrapper.vm.currentStep).toBe(2);
    });

    it('navigates back to step 1 when back clicked', async () => {
      wrapper.vm.currentStep = 2;
      await wrapper.vm.prevStep();

      expect(wrapper.vm.currentStep).toBe(1);
    });

    it('pre-fills data when moving to step 3', async () => {
      wrapper.vm.selectedMethod = 'url';
      wrapper.vm.selectedFeed = {
        url: 'https://techcrunch.com/feed/',
        title: 'TechCrunch',
        description: 'Tech news'
      };
      wrapper.vm.currentStep = 2;

      await wrapper.vm.nextStep();

      expect(wrapper.vm.currentStep).toBe(3);
      expect(wrapper.vm.feedName).toBe('TechCrunch');
      expect(wrapper.vm.feedDescription).toBe('Tech news');
    });
  });

  describe('Accessibility', () => {
    it('has proper ARIA attributes', () => {
      wrapper = mount(AddSourceModal, {
        props: { show: true }
      });

      const modal = wrapper.find('[role="dialog"]');
      expect(modal.exists()).toBe(true);
      expect(modal.attributes('aria-modal')).toBe('true');
      expect(modal.attributes('aria-labelledby')).toBe('modal-title');
    });

    it('has ARIA live regions for status messages', async () => {
      wrapper = mount(AddSourceModal, {
        props: { show: true }
      });

      wrapper.vm.selectedMethod = 'rss';
      wrapper.vm.currentStep = 2;
      wrapper.vm.validationResult = { is_valid: true, feed_metadata: {} };
      await wrapper.vm.$nextTick();

      const liveRegion = wrapper.find('[role="status"]');
      expect(liveRegion.exists()).toBe(true);
      expect(liveRegion.attributes('aria-live')).toBe('polite');
    });

    it('supports keyboard navigation', async () => {
      wrapper = mount(AddSourceModal, {
        props: { show: true }
      });

      const option = wrapper.findAll('.option-card')[0];
      await option.trigger('keypress.enter');

      expect(wrapper.vm.selectedMethod).toBe('url');
    });
  });

  describe('Utility Functions', () => {
    beforeEach(() => {
      wrapper = mount(AddSourceModal, {
        props: { show: true }
      });
    });

    it('formats dates correctly', () => {
      const now = new Date();
      const tenMinutesAgo = new Date(now - 10 * 60 * 1000);

      const formatted = wrapper.vm.formatDate(tenMinutesAgo.toISOString());
      expect(formatted).toContain('10 minutes ago');
    });

    it('gets error title based on error code', () => {
      const title = wrapper.vm.getErrorTitle('not_found');
      expect(title).toBe('Couldn\'t find this feed');
    });

    it('computes auto-detected name correctly', () => {
      wrapper.vm.selectedMethod = 'url';
      wrapper.vm.selectedFeed = { title: 'Test Feed' };

      expect(wrapper.vm.autoDetectedName).toBe('Test Feed');
    });
  });
});
