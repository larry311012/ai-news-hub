/**
 * Resource Hints Utility
 *
 * Provides methods to add resource hints (preload, prefetch, preconnect)
 * to improve page load performance
 */

class ResourceHints {
  constructor() {
    this.head = document.head;
    this.hints = new Set();
  }

  /**
   * Add a preload hint for critical resources
   * @param {string} href - URL of the resource
   * @param {string} as - Type of resource (script, style, font, image, etc.)
   * @param {object} options - Additional options
   */
  preload(href, as, options = {}) {
    const key = `preload:${href}:${as}`;
    if (this.hints.has(key)) return;

    const link = document.createElement('link');
    link.rel = 'preload';
    link.href = href;
    link.as = as;

    if (options.type) link.type = options.type;
    if (options.crossorigin) link.crossOrigin = options.crossorigin;
    if (options.media) link.media = options.media;

    this.head.appendChild(link);
    this.hints.add(key);

    return link;
  }

  /**
   * Add a prefetch hint for future navigation resources
   * @param {string} href - URL of the resource
   */
  prefetch(href) {
    const key = `prefetch:${href}`;
    if (this.hints.has(key)) return;

    const link = document.createElement('link');
    link.rel = 'prefetch';
    link.href = href;

    this.head.appendChild(link);
    this.hints.add(key);

    return link;
  }

  /**
   * Add a preconnect hint for external domains
   * @param {string} origin - Origin to preconnect to
   * @param {boolean} crossorigin - Whether to use crossorigin
   */
  preconnect(origin, crossorigin = false) {
    const key = `preconnect:${origin}`;
    if (this.hints.has(key)) return;

    const link = document.createElement('link');
    link.rel = 'preconnect';
    link.href = origin;

    if (crossorigin) link.crossOrigin = '';

    this.head.appendChild(link);
    this.hints.add(key);

    // Also add dns-prefetch as fallback
    const dnsPrefetch = document.createElement('link');
    dnsPrefetch.rel = 'dns-prefetch';
    dnsPrefetch.href = origin;
    this.head.appendChild(dnsPrefetch);

    return link;
  }

  /**
   * Preload critical fonts
   * @param {string} href - URL of the font file
   * @param {string} type - Font type (woff2, woff, etc.)
   */
  preloadFont(href, type = 'font/woff2') {
    return this.preload(href, 'font', {
      type,
      crossorigin: 'anonymous'
    });
  }

  /**
   * Preload critical images
   * @param {string} href - URL of the image
   * @param {string} type - Image type
   */
  preloadImage(href, type) {
    return this.preload(href, 'image', { type });
  }

  /**
   * Preload critical scripts
   * @param {string} href - URL of the script
   */
  preloadScript(href) {
    return this.preload(href, 'script');
  }

  /**
   * Preload critical styles
   * @param {string} href - URL of the stylesheet
   */
  preloadStyle(href) {
    return this.preload(href, 'style');
  }

  /**
   * Prefetch page for future navigation
   * @param {string} href - URL of the page
   */
  prefetchPage(href) {
    return this.prefetch(href);
  }

  /**
   * Setup preconnect for common third-party origins
   */
  setupCommonPreconnects() {
    // Add common third-party origins here
    const origins = [
      // Add your API server
      import.meta.env.VITE_API_URL,
      // Add CDN origins if any
    ].filter(Boolean);

    origins.forEach(origin => {
      try {
        const url = new URL(origin);
        this.preconnect(url.origin, true);
      } catch (e) {
        console.warn('Invalid origin for preconnect:', origin);
      }
    });
  }

  /**
   * Remove a resource hint
   * @param {string} rel - Relation type
   * @param {string} href - URL of the resource
   */
  remove(rel, href) {
    const link = this.head.querySelector(`link[rel="${rel}"][href="${href}"]`);
    if (link) {
      link.remove();
      this.hints.delete(`${rel}:${href}`);
    }
  }

  /**
   * Clear all resource hints
   */
  clear() {
    const links = this.head.querySelectorAll('link[rel^="pre"]');
    links.forEach(link => link.remove());
    this.hints.clear();
  }
}

// Create singleton instance
const resourceHints = new ResourceHints();

// Auto-setup common preconnects
if (typeof window !== 'undefined') {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      resourceHints.setupCommonPreconnects();
    });
  } else {
    resourceHints.setupCommonPreconnects();
  }
}

export default resourceHints;
