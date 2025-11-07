import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { showToast, toast } from '../utils/toast.js'

describe('Toast Notifications', () => {
  beforeEach(() => {
    // Clean up any existing toasts
    document.body.innerHTML = ''
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.useRealTimers()
    document.body.innerHTML = ''
  })

  describe('Toast Container', () => {
    it('should create toast container if not exists', () => {
      showToast('Test message')

      const container = document.getElementById('toast-container')
      expect(container).toBeTruthy()
      expect(container.className).toContain('fixed')
      expect(container.className).toContain('top-4')
      expect(container.className).toContain('right-4')
    })

    it('should reuse existing toast container', () => {
      showToast('Message 1')
      showToast('Message 2')

      const containers = document.querySelectorAll('#toast-container')
      expect(containers.length).toBe(1)
    })

    it('should have correct positioning styles', () => {
      showToast('Test')

      const container = document.getElementById('toast-container')
      expect(container.style.position).toBe('fixed')
      expect(container.style.top).toBe('1rem')
      expect(container.style.right).toBe('1rem')
    })
  })

  describe('Toast Creation', () => {
    it('should create toast element with message', () => {
      const message = 'Test notification'
      showToast(message)

      // Wait for animation
      vi.advanceTimersByTime(20)

      const container = document.getElementById('toast-container')
      const toast = container.querySelector('div')

      expect(toast).toBeTruthy()
      expect(toast.textContent).toBe(message)
    })

    it('should return toast element', () => {
      const toastElement = showToast('Test')
      expect(toastElement).toBeTruthy()
      expect(toastElement.tagName).toBe('DIV')
    })

    it('should have max-width constraint', () => {
      showToast('Very long message that should be constrained')

      const container = document.getElementById('toast-container')
      const toast = container.querySelector('div')

      expect(toast.className).toContain('max-w-sm')
    })
  })

  describe('Toast Types', () => {
    it('should create info toast (default)', () => {
      showToast('Info message')

      const container = document.getElementById('toast-container')
      const toast = container.querySelector('div')

      expect(toast.className).toContain('bg-blue-500')
    })

    it('should create success toast', () => {
      showToast('Success message', 'success')

      const container = document.getElementById('toast-container')
      const toast = container.querySelector('div')

      expect(toast.className).toContain('bg-green-500')
    })

    it('should create warning toast', () => {
      showToast('Warning message', 'warning')

      const container = document.getElementById('toast-container')
      const toast = container.querySelector('div')

      expect(toast.className).toContain('bg-yellow-500')
    })

    it('should create error toast', () => {
      showToast('Error message', 'error')

      const container = document.getElementById('toast-container')
      const toast = container.querySelector('div')

      expect(toast.className).toContain('bg-red-500')
    })

    it('should default to info for invalid type', () => {
      showToast('Message', 'invalid-type')

      const container = document.getElementById('toast-container')
      const toast = container.querySelector('div')

      expect(toast.className).toContain('bg-blue-500')
    })
  })

  describe('Toast Styling', () => {
    it('should have white text', () => {
      showToast('Test')

      const container = document.getElementById('toast-container')
      const toast = container.querySelector('div')

      expect(toast.className).toContain('text-white')
    })

    it('should have padding', () => {
      showToast('Test')

      const container = document.getElementById('toast-container')
      const toast = container.querySelector('div')

      expect(toast.className).toContain('px-6')
      expect(toast.className).toContain('py-3')
    })

    it('should have rounded corners', () => {
      showToast('Test')

      const container = document.getElementById('toast-container')
      const toast = container.querySelector('div')

      expect(toast.className).toContain('rounded-lg')
    })

    it('should have shadow', () => {
      showToast('Test')

      const container = document.getElementById('toast-container')
      const toast = container.querySelector('div')

      expect(toast.className).toContain('shadow-lg')
    })
  })

  describe('Toast Animation', () => {
    it('should start with opacity-0 and translate-x-full', () => {
      showToast('Test')

      const container = document.getElementById('toast-container')
      const toast = container.querySelector('div')

      expect(toast.className).toContain('opacity-0')
      expect(toast.className).toContain('translate-x-full')
    })

    it('should animate in after delay', () => {
      showToast('Test')

      const container = document.getElementById('toast-container')
      const toast = container.querySelector('div')

      // Initially hidden
      expect(toast.className).toContain('opacity-0')

      // After animation delay
      vi.advanceTimersByTime(20)

      expect(toast.style.opacity).toBe('1')
      expect(toast.style.transform).toBe('translateX(0)')
    })

    it('should animate out before removal', () => {
      showToast('Test', 'info', 1000)

      const container = document.getElementById('toast-container')
      let toast = container.querySelector('div')

      // Animate in
      vi.advanceTimersByTime(20)

      // Wait for auto-dismiss
      vi.advanceTimersByTime(1000)

      toast = container.querySelector('div')
      if (toast) {
        expect(toast.style.opacity).toBe('0')
        expect(toast.style.transform).toBe('translateX(100%)')
      }
    })
  })

  describe('Toast Auto-Dismiss', () => {
    it('should auto-dismiss after default duration (3000ms)', () => {
      showToast('Temporary message')

      const container = document.getElementById('toast-container')

      // Toast should exist initially
      let toast = container.querySelector('div')
      expect(toast).toBeTruthy()

      // Fast-forward past auto-dismiss + animation
      vi.advanceTimersByTime(3400)

      // Toast should be removed
      toast = container.querySelector('div')
      expect(toast).toBeFalsy()
    })

    it('should respect custom duration', () => {
      showToast('Custom duration', 'info', 5000)

      const container = document.getElementById('toast-container')

      // Still visible at 3 seconds
      vi.advanceTimersByTime(3000)
      let toast = container.querySelector('div')
      expect(toast).toBeTruthy()

      // Removed after 5 seconds + animation
      vi.advanceTimersByTime(2400)
      toast = container.querySelector('div')
      expect(toast).toBeFalsy()
    })

    it('should handle very short durations', () => {
      showToast('Quick', 'info', 100)

      // Advance past the duration + animation time
      vi.advanceTimersByTime(500)

      // Container might be removed entirely if empty
      const container = document.getElementById('toast-container')
      if (container) {
        const toast = container.querySelector('div')
        expect(toast).toBeFalsy()
      } else {
        // Container was cleaned up, which is also valid
        expect(container).toBeFalsy()
      }
    })
  })

  describe('Multiple Toasts', () => {
    it('should stack multiple toasts', () => {
      showToast('Message 1', 'info')
      showToast('Message 2', 'success')
      showToast('Message 3', 'error')

      const container = document.getElementById('toast-container')
      expect(container.children.length).toBe(3)
    })

    it('should remove toasts independently', () => {
      showToast('Short', 'info', 1000)
      showToast('Long', 'success', 5000)

      const container = document.getElementById('toast-container')

      // After 1.4 seconds (1000ms + 300ms animation + buffer), short toast removed
      vi.advanceTimersByTime(1400)

      const toasts = container.querySelectorAll('div')
      expect(toasts.length).toBe(1)
      expect(toasts[0].textContent).toBe('Long')
    })

    it('should maintain correct order', () => {
      showToast('First', 'info')
      showToast('Second', 'info')
      showToast('Third', 'info')

      vi.advanceTimersByTime(20)

      const container = document.getElementById('toast-container')
      const toasts = Array.from(container.querySelectorAll('div'))

      expect(toasts[0].textContent).toBe('First')
      expect(toasts[1].textContent).toBe('Second')
      expect(toasts[2].textContent).toBe('Third')
    })
  })

  describe('Container Cleanup', () => {
    it('should remove container when empty', () => {
      showToast('Test', 'info', 1000)

      // Wait for toast to be removed
      vi.advanceTimersByTime(1400)

      const container = document.getElementById('toast-container')
      expect(container).toBeFalsy()
    })

    it('should keep container if other toasts exist', () => {
      showToast('Short', 'info', 1000)
      showToast('Long', 'info', 5000)

      // Remove short toast
      vi.advanceTimersByTime(1400)

      const container = document.getElementById('toast-container')
      expect(container).toBeTruthy()
      expect(container.children.length).toBe(1)
    })
  })

  describe('XSS Protection', () => {
    it('should use textContent to prevent XSS', () => {
      const maliciousInput = '<script>alert("XSS")</script>'
      showToast(maliciousInput)

      const container = document.getElementById('toast-container')
      const toast = container.querySelector('div')

      // Should display as text, not execute
      expect(toast.innerHTML).not.toContain('<script>')
      expect(toast.textContent).toBe(maliciousInput)
    })

    it('should escape HTML entities', () => {
      const htmlInput = '<b>Bold</b> and <i>italic</i>'
      showToast(htmlInput)

      const container = document.getElementById('toast-container')
      const toast = container.querySelector('div')

      expect(toast.textContent).toBe(htmlInput)
      expect(toast.querySelector('b')).toBeFalsy()
      expect(toast.querySelector('i')).toBeFalsy()
    })

    it('should not execute event handlers in message', () => {
      const eventSpy = vi.fn()
      window.testCallback = eventSpy

      showToast('<img src=x onerror="window.testCallback()"/>')

      vi.advanceTimersByTime(100)
      expect(eventSpy).not.toHaveBeenCalled()
    })
  })

  describe('Toast Helper Methods', () => {
    it('should have info helper method', () => {
      const toastElement = toast.info('Info message')
      expect(toastElement).toBeTruthy()

      const toastDiv = document.querySelector('.bg-blue-500')
      expect(toastDiv).toBeTruthy()
    })

    it('should have success helper method', () => {
      const toastElement = toast.success('Success message')
      expect(toastElement).toBeTruthy()

      const toastDiv = document.querySelector('.bg-green-500')
      expect(toastDiv).toBeTruthy()
    })

    it('should have warning helper method', () => {
      const toastElement = toast.warning('Warning message')
      expect(toastElement).toBeTruthy()

      const toastDiv = document.querySelector('.bg-yellow-500')
      expect(toastDiv).toBeTruthy()
    })

    it('should have error helper method', () => {
      const toastElement = toast.error('Error message')
      expect(toastElement).toBeTruthy()

      const toastDiv = document.querySelector('.bg-red-500')
      expect(toastDiv).toBeTruthy()
    })

    it('should support custom duration in helper methods', () => {
      toast.success('Quick success', 500)

      vi.advanceTimersByTime(900)

      const container = document.getElementById('toast-container')
      expect(container?.children.length || 0).toBe(0)
    })
  })

  describe('Global Availability', () => {
    it('should be available on window object', () => {
      expect(window.showToast).toBe(showToast)
      expect(window.toast).toBe(toast)
    })
  })

  describe('Edge Cases', () => {
    it('should handle empty message', () => {
      showToast('')

      const container = document.getElementById('toast-container')
      const toast = container.querySelector('div')

      expect(toast).toBeTruthy()
      expect(toast.textContent).toBe('')
    })

    it('should handle very long messages', () => {
      const longMessage = 'A'.repeat(500)
      showToast(longMessage)

      const container = document.getElementById('toast-container')
      const toast = container.querySelector('div')

      expect(toast.textContent).toBe(longMessage)
      expect(toast.className).toContain('max-w-sm')
    })

    it('should handle special characters', () => {
      const specialChars = '!@#$%^&*()_+-=[]{}|;:",.<>?/~`'
      showToast(specialChars)

      const container = document.getElementById('toast-container')
      const toast = container.querySelector('div')

      expect(toast.textContent).toBe(specialChars)
    })

    it('should handle unicode characters', () => {
      const unicode = '你好世界 🌍 مرحبا'
      showToast(unicode)

      const container = document.getElementById('toast-container')
      const toast = container.querySelector('div')

      expect(toast.textContent).toBe(unicode)
    })
  })
})
