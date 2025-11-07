/**
 * Lazy Loading Utility
 *
 * Provides intersection observer-based lazy loading for images and other content
 * Improves initial page load performance by deferring off-screen content
 */

class LazyLoader {
  constructor(options = {}) {
    this.options = {
      root: null,
      rootMargin: '50px', // Load 50px before element comes into view
      threshold: 0.01,
      ...options
    };

    this.observer = null;
    this.init();
  }

  init() {
    // Check if IntersectionObserver is supported
    if (!('IntersectionObserver' in window)) {
      console.warn('IntersectionObserver not supported, loading all content immediately');
      this.loadAllImmediately();
      return;
    }

    this.observer = new IntersectionObserver(
      this.handleIntersection.bind(this),
      this.options
    );
  }

  handleIntersection(entries) {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const element = entry.target;
        this.loadElement(element);
        this.observer.unobserve(element);
      }
    });
  }

  loadElement(element) {
    const tagName = element.tagName.toLowerCase();

    if (tagName === 'img') {
      this.loadImage(element);
    } else if (tagName === 'iframe') {
      this.loadIframe(element);
    } else if (element.hasAttribute('data-lazy-component')) {
      this.loadComponent(element);
    }
  }

  loadImage(img) {
    const src = img.getAttribute('data-src');
    const srcset = img.getAttribute('data-srcset');

    if (!src && !srcset) return;

    // Show loading state
    img.classList.add('lazy-loading');

    const loadHandler = () => {
      img.classList.remove('lazy-loading');
      img.classList.add('lazy-loaded');
      img.removeEventListener('load', loadHandler);
      img.removeEventListener('error', errorHandler);
    };

    const errorHandler = () => {
      img.classList.remove('lazy-loading');
      img.classList.add('lazy-error');
      img.removeEventListener('load', loadHandler);
      img.removeEventListener('error', errorHandler);
    };

    img.addEventListener('load', loadHandler);
    img.addEventListener('error', errorHandler);

    if (srcset) {
      img.srcset = srcset;
    }
    if (src) {
      img.src = src;
    }
  }

  loadIframe(iframe) {
    const src = iframe.getAttribute('data-src');
    if (!src) return;

    iframe.src = src;
    iframe.classList.add('lazy-loaded');
  }

  loadComponent(element) {
    const componentName = element.getAttribute('data-lazy-component');
    const event = new CustomEvent('lazyload', {
      detail: { componentName }
    });
    element.dispatchEvent(event);
    element.classList.add('lazy-loaded');
  }

  observe(element) {
    if (!this.observer) {
      this.loadElement(element);
      return;
    }

    this.observer.observe(element);
  }

  observeAll(selector = '[data-src]') {
    const elements = document.querySelectorAll(selector);
    elements.forEach(element => this.observe(element));
  }

  loadAllImmediately() {
    const elements = document.querySelectorAll('[data-src]');
    elements.forEach(element => this.loadElement(element));
  }

  disconnect() {
    if (this.observer) {
      this.observer.disconnect();
    }
  }
}

// Vue directive for lazy loading
export const vLazyLoad = {
  mounted(el, binding) {
    const loader = new LazyLoader(binding.value || {});
    loader.observe(el);

    // Store loader instance for cleanup
    el._lazyLoader = loader;
  },
  unmounted(el) {
    if (el._lazyLoader) {
      el._lazyLoader.disconnect();
      delete el._lazyLoader;
    }
  }
};

// Default export for standalone usage
export default LazyLoader;

// Auto-initialize for images with data-src attribute
if (typeof window !== 'undefined') {
  const autoLazyLoad = () => {
    const loader = new LazyLoader();
    loader.observeAll('[data-src]');

    // Store on window for manual control if needed
    window.lazyLoader = loader;
  };

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', autoLazyLoad);
  } else {
    autoLazyLoad();
  }
}
