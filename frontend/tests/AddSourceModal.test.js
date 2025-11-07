import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount } from '@vue/test-utils';
import AddSourceModal from '../components/AddSourceModal.vue';

// Mock fetch globally
global.fetch = vi.fn();
global.localStorage = {
    getItem: vi.fn(() => 'mock-token'),
    setItem: vi.fn(),
    removeItem: vi.fn(),
    clear: vi.fn()
};

describe('AddSourceModal', () => {
    let wrapper;

    beforeEach(() => {
        vi.clearAllMocks();
    });

    afterEach(() => {
        if (wrapper) {
            wrapper.unmount();
        }
    });

    describe('Component Rendering', () => {
        it('renders modal when show prop is true', () => {
            wrapper = mount(AddSourceModal, {
                props: { show: true }
            });

            expect(wrapper.find('[role="dialog"]').exists()).toBe(true);
            expect(wrapper.find('#modal-title').text()).toBe('Add News Source');
        });

        it('does not render modal when show prop is false', () => {
            wrapper = mount(AddSourceModal, {
                props: { show: false }
            });

            expect(wrapper.find('[role="dialog"]').exists()).toBe(false);
        });

        it('displays step 1 by default', () => {
            wrapper = mount(AddSourceModal, {
                props: { show: true }
            });

            expect(wrapper.text()).toContain('How would you like to add a source?');
            expect(wrapper.text()).toContain('Enter Website URL');
            expect(wrapper.text()).toContain('I have a feed URL');
        });

        it('shows step indicator correctly', () => {
            wrapper = mount(AddSourceModal, {
                props: { show: true }
            });

            expect(wrapper.text()).toContain('Step 1 of 3');
        });
    });

    describe('Step 1: Method Selection', () => {
        beforeEach(() => {
            wrapper = mount(AddSourceModal, {
                props: { show: true }
            });
        });

        it('allows selecting Website URL method', async () => {
            const urlOption = wrapper.findAll('.option-card')[0];
            await urlOption.trigger('click');

            expect(wrapper.vm.selectedMethod).toBe('url');
            expect(urlOption.classes()).toContain('border-indigo-600');
        });

        it('allows selecting RSS Feed URL method', async () => {
            const rssOption = wrapper.findAll('.option-card')[1];
            await rssOption.trigger('click');

            expect(wrapper.vm.selectedMethod).toBe('rss');
            expect(rssOption.classes()).toContain('border-indigo-600');
        });

        it('disables Continue button when no method selected', () => {
            const continueBtn = wrapper.find('button:contains("Continue")');
            expect(continueBtn.attributes('disabled')).toBeDefined();
        });

        it('enables Continue button when method selected', async () => {
            await wrapper.findAll('.option-card')[0].trigger('click');
            await wrapper.vm.$nextTick();

            const continueBtn = wrapper.find('button');
            const continueButtons = wrapper.findAll('button').filter(w =>
                w.text().includes('Continue')
            );

            expect(wrapper.vm.canProceedToNextStep).toBe(true);
        });

        it('advances to step 2 when Continue is clicked', async () => {
            await wrapper.findAll('.option-card')[0].trigger('click');
            await wrapper.vm.$nextTick();

            // Find and click Continue button
            const buttons = wrapper.findAll('button');
            const continueButton = buttons.find(b => b.text().includes('Continue'));
            await continueButton.trigger('click');

            expect(wrapper.vm.currentStep).toBe(2);
        });
    });

    describe('Step 2: Website URL Discovery', () => {
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
            expect(wrapper.find('#website-url').attributes('placeholder')).toBe('https://techcrunch.com');
        });

        it('discovers feeds from URL', async () => {
            const mockFeeds = [
                {
                    url: 'https://techcrunch.com/feed/',
                    title: 'TechCrunch',
                    description: 'Latest tech news',
                    type: 'rss',
                    item_count: 25
                }
            ];

            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ discovered_feeds: mockFeeds })
            });

            wrapper.vm.websiteUrl = 'https://techcrunch.com';
            await wrapper.vm.handleDiscovery();

            expect(fetch).toHaveBeenCalledWith(
                '/api/user-feeds/discover',
                expect.objectContaining({
                    method: 'POST',
                    headers: expect.objectContaining({
                        'Authorization': 'Bearer mock-token'
                    }),
                    body: JSON.stringify({ website_url: 'https://techcrunch.com' })
                })
            );

            expect(wrapper.vm.discoveredFeeds).toEqual(mockFeeds);
            expect(wrapper.vm.selectedFeed).toEqual(mockFeeds[0]); // Auto-select single feed
        });

        it('shows loading state during discovery', async () => {
            fetch.mockImplementationOnce(() => new Promise(() => {})); // Never resolves

            wrapper.vm.websiteUrl = 'https://techcrunch.com';
            const discoveryPromise = wrapper.vm.handleDiscovery();
            await wrapper.vm.$nextTick();

            expect(wrapper.vm.discovering).toBe(true);
            expect(wrapper.text()).toContain('Searching for feeds...');
        });

        it('displays discovered feeds as selectable options', async () => {
            const mockFeeds = [
                {
                    url: 'https://techcrunch.com/feed/',
                    title: 'TechCrunch',
                    description: 'Latest tech news',
                    type: 'rss',
                    item_count: 25
                },
                {
                    url: 'https://techcrunch.com/startups/feed/',
                    title: 'TechCrunch - Startups',
                    description: 'Startup news',
                    type: 'rss',
                    item_count: 15
                }
            ];

            wrapper.vm.discoveredFeeds = mockFeeds;
            wrapper.vm.discovering = false;
            wrapper.vm.attemptedDiscovery = true;
            await wrapper.vm.$nextTick();

            expect(wrapper.text()).toContain('Found 2 feed(s)');
            expect(wrapper.text()).toContain('TechCrunch');
            expect(wrapper.text()).toContain('TechCrunch - Startups');
        });

        it('shows "no feeds found" error state', async () => {
            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ discovered_feeds: [] })
            });

            wrapper.vm.websiteUrl = 'https://example.com';
            await wrapper.vm.handleDiscovery();

            expect(wrapper.text()).toContain('No feeds found');
            expect(wrapper.text()).toContain('Switch to direct URL entry');
        });

        it('allows switching to RSS method from no feeds error', async () => {
            wrapper.vm.discoveredFeeds = [];
            wrapper.vm.attemptedDiscovery = true;
            await wrapper.vm.$nextTick();

            const switchButton = wrapper.find('button:contains("Switch to direct URL entry")');
            await switchButton.trigger('click');

            expect(wrapper.vm.selectedMethod).toBe('rss');
            expect(wrapper.vm.currentStep).toBe(1);
        });
    });

    describe('Step 2: RSS Feed Validation', () => {
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
            expect(wrapper.find('#feed-url').attributes('placeholder')).toBe('https://techcrunch.com/feed/');
        });

        it('validates feed successfully', async () => {
            const mockValidation = {
                is_valid: true,
                feed_metadata: {
                    title: 'TechCrunch',
                    description: 'Latest tech news',
                    type: 'rss',
                    item_count: 25
                }
            };

            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => mockValidation
            });

            wrapper.vm.feedUrl = 'https://techcrunch.com/feed/';
            await wrapper.vm.handleValidation();

            expect(fetch).toHaveBeenCalledWith(
                '/api/user-feeds/validate',
                expect.objectContaining({
                    method: 'POST',
                    body: JSON.stringify({ feed_url: 'https://techcrunch.com/feed/' })
                })
            );

            expect(wrapper.vm.validationResult).toEqual(mockValidation);
            expect(wrapper.vm.validationError).toBeNull();
        });

        it('shows success state after validation', async () => {
            wrapper.vm.validationResult = {
                is_valid: true,
                feed_metadata: {
                    title: 'TechCrunch',
                    item_count: 25
                }
            };
            await wrapper.vm.$nextTick();

            expect(wrapper.text()).toContain('Feed validated successfully!');
            expect(wrapper.text()).toContain('TechCrunch');
        });

        it('handles validation errors', async () => {
            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    is_valid: false,
                    error_message: 'Feed not found (404)',
                    error_code: 'not_found'
                })
            });

            wrapper.vm.feedUrl = 'https://example.com/invalid-feed.xml';
            await wrapper.vm.handleValidation();

            expect(wrapper.vm.validationError).toBe('Feed not found (404)');
            expect(wrapper.vm.validationErrorTitle).toBe('Couldn\'t find this feed');
        });

        it('shows error state with retry button', async () => {
            wrapper.vm.validationError = 'Feed not found (404)';
            wrapper.vm.validationErrorTitle = 'Couldn\'t find this feed';
            await wrapper.vm.$nextTick();

            expect(wrapper.text()).toContain('Couldn\'t find this feed');
            expect(wrapper.text()).toContain('Feed not found (404)');
            expect(wrapper.find('button:contains("Try again")').exists()).toBe(true);
        });

        it('allows retrying validation', async () => {
            wrapper.vm.validationError = 'Connection failed';
            await wrapper.vm.$nextTick();

            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    is_valid: true,
                    feed_metadata: { title: 'Test Feed' }
                })
            });

            const retryButton = wrapper.find('button:contains("Try again")');
            await retryButton.trigger('click');

            expect(wrapper.vm.validationError).toBeNull();
        });
    });

    describe('Step 3: Configure & Preview', () => {
        beforeEach(async () => {
            wrapper = mount(AddSourceModal, {
                props: { show: true }
            });
            wrapper.vm.selectedMethod = 'url';
            wrapper.vm.selectedFeed = {
                url: 'https://techcrunch.com/feed/',
                title: 'TechCrunch',
                description: 'Latest tech news'
            };
            wrapper.vm.currentStep = 3;
            await wrapper.vm.$nextTick();
        });

        it('displays configuration form', () => {
            expect(wrapper.find('#feed-name').exists()).toBe(true);
            expect(wrapper.find('#update-frequency').exists()).toBe(true);
        });

        it('pre-fills feed name from auto-detected name', () => {
            expect(wrapper.vm.feedName).toBe('TechCrunch');
        });

        it('has default update frequency of 1 hour', () => {
            expect(wrapper.vm.updateFrequency).toBe(3600);
        });

        it('displays all update frequency options', () => {
            const select = wrapper.find('#update-frequency');
            const options = select.findAll('option');

            expect(options).toHaveLength(5);
            expect(options[0].text()).toContain('30 minutes');
            expect(options[1].text()).toContain('hour (recommended)');
            expect(options[4].text()).toContain('Once a day');
        });

        it('shows preview section when preview items available', async () => {
            wrapper.vm.previewItems = [
                {
                    title: 'Breaking News 1',
                    published_date: new Date().toISOString()
                },
                {
                    title: 'Breaking News 2',
                    published_date: new Date().toISOString()
                }
            ];
            await wrapper.vm.$nextTick();

            expect(wrapper.text()).toContain('Preview');
            expect(wrapper.text()).toContain('Breaking News 1');
        });
    });

    describe('Add Feed', () => {
        beforeEach(async () => {
            wrapper = mount(AddSourceModal, {
                props: { show: true }
            });
            wrapper.vm.selectedMethod = 'url';
            wrapper.vm.selectedFeed = {
                url: 'https://techcrunch.com/feed/',
                title: 'TechCrunch'
            };
            wrapper.vm.feedName = 'TechCrunch News';
            wrapper.vm.updateFrequency = 3600;
            wrapper.vm.currentStep = 3;
            await wrapper.vm.$nextTick();
        });

        it('successfully adds feed', async () => {
            const mockFeed = {
                id: 1,
                feed_name: 'TechCrunch News',
                feed_url: 'https://techcrunch.com/feed/',
                health_status: 'unknown'
            };

            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ feed: mockFeed })
            });

            await wrapper.vm.handleAddFeed();

            expect(fetch).toHaveBeenCalledWith(
                '/api/user-feeds',
                expect.objectContaining({
                    method: 'POST',
                    body: JSON.stringify({
                        feed_url: 'https://techcrunch.com/feed/',
                        feed_name: 'TechCrunch News',
                        feed_description: undefined,
                        update_frequency: 3600
                    })
                })
            );

            expect(wrapper.emitted('added')).toBeTruthy();
            expect(wrapper.emitted('added')[0][0]).toEqual(mockFeed);
        });

        it('shows loading state during add', async () => {
            fetch.mockImplementationOnce(() => new Promise(() => {})); // Never resolves

            const addPromise = wrapper.vm.handleAddFeed();
            await wrapper.vm.$nextTick();

            expect(wrapper.vm.adding).toBe(true);
            expect(wrapper.text()).toContain('Adding...');
        });

        it('handles add errors gracefully', async () => {
            fetch.mockRejectedValueOnce(new Error('Network error'));

            // Mock showToast to track error
            const toastSpy = vi.spyOn(wrapper.vm, 'showToast');

            await wrapper.vm.handleAddFeed();

            expect(wrapper.vm.adding).toBe(false);
            expect(toastSpy).toHaveBeenCalledWith(
                expect.stringContaining('Failed'),
                'Error',
                'error'
            );
        });

        it('disables Add button when feed name is empty', async () => {
            wrapper.vm.feedName = '';
            await wrapper.vm.$nextTick();

            const addButton = wrapper.findAll('button').find(b =>
                b.text().includes('Add Source')
            );

            expect(addButton.attributes('disabled')).toBeDefined();
        });
    });

    describe('Modal Navigation', () => {
        beforeEach(() => {
            wrapper = mount(AddSourceModal, {
                props: { show: true }
            });
        });

        it('shows Back button on step 2 and 3', async () => {
            wrapper.vm.currentStep = 2;
            await wrapper.vm.$nextTick();

            expect(wrapper.find('button:contains("Back")').exists()).toBe(true);
        });

        it('navigates back when Back button clicked', async () => {
            wrapper.vm.currentStep = 2;
            await wrapper.vm.$nextTick();

            await wrapper.find('button:contains("Back")').trigger('click');

            expect(wrapper.vm.currentStep).toBe(1);
        });

        it('closes modal on close button click', async () => {
            const closeButton = wrapper.find('[aria-label="Close modal"]');
            await closeButton.trigger('click');

            expect(wrapper.emitted('close')).toBeTruthy();
        });

        it('closes modal on ESC key', async () => {
            const escapeEvent = new KeyboardEvent('keydown', { key: 'Escape' });
            document.dispatchEvent(escapeEvent);
            await wrapper.vm.$nextTick();

            expect(wrapper.emitted('close')).toBeTruthy();
        });

        it('resets modal state after closing', async () => {
            wrapper.vm.selectedMethod = 'url';
            wrapper.vm.websiteUrl = 'https://example.com';
            wrapper.vm.currentStep = 2;

            wrapper.vm.resetModal();

            expect(wrapper.vm.currentStep).toBe(1);
            expect(wrapper.vm.selectedMethod).toBeNull();
            expect(wrapper.vm.websiteUrl).toBe('');
        });
    });

    describe('Accessibility', () => {
        beforeEach(() => {
            wrapper = mount(AddSourceModal, {
                props: { show: true }
            });
        });

        it('has proper ARIA attributes', () => {
            const dialog = wrapper.find('[role="dialog"]');
            expect(dialog.attributes('aria-modal')).toBe('true');
            expect(dialog.attributes('aria-labelledby')).toBe('modal-title');
        });

        it('has accessible form labels', async () => {
            wrapper.vm.currentStep = 2;
            wrapper.vm.selectedMethod = 'url';
            await wrapper.vm.$nextTick();

            const label = wrapper.find('label[for="website-url"]');
            expect(label.exists()).toBe(true);
        });

        it('supports keyboard navigation on options', () => {
            const options = wrapper.findAll('.option-card');
            options.forEach(option => {
                expect(option.attributes('tabindex')).toBe('0');
                expect(option.attributes('role')).toBe('button');
            });
        });

        it('has aria-live regions for dynamic content', async () => {
            wrapper.vm.selectedMethod = 'url';
            wrapper.vm.currentStep = 2;
            wrapper.vm.discoveredFeeds = [];
            wrapper.vm.attemptedDiscovery = true;
            await wrapper.vm.$nextTick();

            const alert = wrapper.find('[role="alert"]');
            expect(alert.exists()).toBe(true);
            expect(alert.attributes('aria-live')).toBe('polite');
        });
    });

    describe('Utility Methods', () => {
        beforeEach(() => {
            wrapper = mount(AddSourceModal, {
                props: { show: true }
            });
        });

        it('formats dates correctly', () => {
            const now = new Date();
            const fiveMinutesAgo = new Date(now.getTime() - 5 * 60 * 1000);
            const twoDaysAgo = new Date(now.getTime() - 2 * 24 * 60 * 60 * 1000);

            expect(wrapper.vm.formatDate(fiveMinutesAgo.toISOString())).toContain('minutes ago');
            expect(wrapper.vm.formatDate(twoDaysAgo.toISOString())).toContain('days ago');
        });

        it('gets correct error title for error codes', () => {
            expect(wrapper.vm.getErrorTitle('not_found')).toBe('Couldn\'t find this feed');
            expect(wrapper.vm.getErrorTitle('malformed')).toBe('This feed has formatting issues');
            expect(wrapper.vm.getErrorTitle('timeout')).toBe('Connection timed out');
            expect(wrapper.vm.getErrorTitle('invalid_structure')).toBe('This doesn\'t look like a valid feed');
        });

        it('computes auto-detected name correctly', () => {
            wrapper.vm.selectedMethod = 'url';
            wrapper.vm.selectedFeed = { title: 'Test Feed' };
            expect(wrapper.vm.autoDetectedName).toBe('Test Feed');

            wrapper.vm.selectedMethod = 'rss';
            wrapper.vm.validationResult = {
                feed_metadata: { title: 'RSS Feed' }
            };
            expect(wrapper.vm.autoDetectedName).toBe('RSS Feed');
        });
    });
});
