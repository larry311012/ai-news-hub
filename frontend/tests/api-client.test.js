import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { ApiClient, API_BASE_URL } from '../utils/api-client.js'

// Mock fetch globally
global.fetch = vi.fn()

describe('API Client', () => {
  let client

  beforeEach(() => {
    vi.clearAllMocks()
    client = new ApiClient()
    // Clear any pending timers
    vi.clearAllTimers()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Configuration', () => {
    it('should use correct base URL from environment', () => {
      expect(client.baseURL).toBe('http://localhost:8000')
    })

    it('should have 30 second default timeout', () => {
      expect(client.timeout).toBe(30000)
    })

    it('should have default retry attempts', () => {
      expect(client.retryAttempts).toBe(3)
    })

    it('should build full URLs correctly', () => {
      expect(client.buildURL('/api/test')).toBe('http://localhost:8000/api/test')
      expect(client.buildURL('api/test')).toBe('http://localhost:8000/api/test')
      expect(client.buildURL('https://example.com/test')).toBe('https://example.com/test')
    })
  })

  describe('HTTP Methods', () => {
    it('should make GET requests', async () => {
      const mockData = { id: 1, name: 'test' }
      global.fetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => mockData
      })

      const response = await client.get('/api/test')

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/test',
        expect.objectContaining({
          method: 'GET',
          headers: expect.objectContaining({
            'Content-Type': 'application/json'
          })
        })
      )
      expect(response.data).toEqual(mockData)
      expect(response.status).toBe(200)
    })

    it('should make POST requests with data', async () => {
      const postData = { name: 'test', value: 123 }
      const mockResponse = { id: 1, ...postData }

      global.fetch.mockResolvedValueOnce({
        ok: true,
        status: 201,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => mockResponse
      })

      const response = await client.post('/api/test', postData)

      const fetchCall = global.fetch.mock.calls[0]
      expect(fetchCall[0]).toBe('http://localhost:8000/api/test')
      expect(fetchCall[1].method).toBe('POST')
      expect(fetchCall[1].body).toBe(JSON.stringify(postData))
      expect(response.data).toEqual(mockResponse)
    })

    it('should make PUT requests', async () => {
      const putData = { name: 'updated' }
      global.fetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => putData
      })

      await client.put('/api/test/1', putData)

      const fetchCall = global.fetch.mock.calls[0]
      expect(fetchCall[1].method).toBe('PUT')
      expect(fetchCall[1].body).toBe(JSON.stringify(putData))
    })

    it('should make PATCH requests', async () => {
      const patchData = { status: 'active' }
      global.fetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => patchData
      })

      await client.patch('/api/test/1', patchData)

      const fetchCall = global.fetch.mock.calls[0]
      expect(fetchCall[1].method).toBe('PATCH')
    })

    it('should make DELETE requests', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        status: 204,
        headers: new Headers(),
        text: async () => ''
      })

      await client.delete('/api/test/1')

      const fetchCall = global.fetch.mock.calls[0]
      expect(fetchCall[1].method).toBe('DELETE')
    })
  })

  describe('Error Handling', () => {
    it('should handle 401 errors', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({ detail: 'Authentication required' })
      })

      await expect(client.get('/api/protected')).rejects.toThrow('Authentication required')
    })

    it('should handle 403 errors', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 403,
        statusText: 'Forbidden',
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({ detail: 'Access denied' })
      })

      await expect(client.get('/api/admin')).rejects.toThrow('Access denied')
    })

    it('should handle 404 errors', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({ detail: 'Resource not found' })
      })

      await expect(client.get('/api/missing')).rejects.toThrow()
    })

    it('should handle 500 errors', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({ detail: 'Server error' })
      })

      await expect(client.get('/api/broken')).rejects.toThrow('Server error')
    })

    it('should handle network errors', async () => {
      // Mock a proper response structure before the error
      const networkError = new Error('Failed to fetch')
      networkError.name = 'TypeError'

      global.fetch.mockRejectedValueOnce(networkError)

      // The request will retry 3 times before finally failing
      await expect(client.get('/api/test', { retries: 0 })).rejects.toThrow()
    })

    it('should handle non-JSON error responses', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        headers: new Headers({ 'content-type': 'text/html' }),
        json: async () => {
          throw new Error('Not JSON')
        }
      })

      await expect(client.get('/api/broken')).rejects.toThrow()
    })
  })

  describe('Request Options', () => {
    it('should include credentials by default', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({})
      })

      await client.get('/api/test')

      const fetchCall = global.fetch.mock.calls[0]
      expect(fetchCall[1].credentials).toBe('include')
    })

    it('should allow custom headers', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({})
      })

      await client.get('/api/test', {
        headers: {
          'X-Custom-Header': 'test-value'
        }
      })

      const fetchCall = global.fetch.mock.calls[0]
      expect(fetchCall[1].headers['X-Custom-Header']).toBe('test-value')
    })

    it('should respect withCredentials option', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({})
      })

      await client.get('/api/test', { withCredentials: false })

      const fetchCall = global.fetch.mock.calls[0]
      expect(fetchCall[1].credentials).toBe('same-origin')
    })
  })

  describe('Response Handling', () => {
    it('should parse JSON responses', async () => {
      const jsonData = { message: 'success', data: [1, 2, 3] }
      global.fetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => jsonData
      })

      const response = await client.get('/api/test')
      expect(response.data).toEqual(jsonData)
    })

    it('should handle text responses', async () => {
      const textData = 'Plain text response'
      global.fetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'text/plain' }),
        text: async () => textData
      })

      const response = await client.get('/api/test')
      expect(response.data).toBe(textData)
    })

    it('should include response status and headers', async () => {
      const headers = new Headers({
        'content-type': 'application/json',
        'x-custom': 'value'
      })

      global.fetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers,
        json: async () => ({ test: true })
      })

      const response = await client.get('/api/test')
      expect(response.status).toBe(200)
      expect(response.headers).toBeDefined()
    })
  })

  describe('Retry Logic', () => {
    it('should retry on network failures', async () => {
      // Mock: fail twice, then succeed
      global.fetch
        .mockRejectedValueOnce(new Error('Failed to fetch'))
        .mockRejectedValueOnce(new Error('Failed to fetch'))
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({ success: true })
        })

      const response = await client.get('/api/test')

      expect(global.fetch).toHaveBeenCalledTimes(3)
      expect(response.data).toEqual({ success: true })
    })

    it('should respect retry limit', async () => {
      // Mock: always fail
      global.fetch.mockRejectedValue(new Error('Failed to fetch'))

      await expect(client.get('/api/test')).rejects.toThrow('Failed to fetch')

      // Should try initial + 3 retries = 4 total
      expect(global.fetch).toHaveBeenCalledTimes(4)
    })

    it('should not retry on 4xx client errors', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        statusText: 'Bad Request',
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({ detail: 'Invalid request' })
      })

      await expect(client.get('/api/test')).rejects.toThrow()

      // Should only try once (no retries on client errors)
      expect(global.fetch).toHaveBeenCalledTimes(1)
    })
  })

  describe('File Upload', () => {
    it('should upload files with FormData', async () => {
      const mockFile = new File(['test content'], 'test.txt', { type: 'text/plain' })

      // Mock XMLHttpRequest
      const mockXHR = {
        open: vi.fn(),
        send: vi.fn(),
        setRequestHeader: vi.fn(),
        upload: {
          addEventListener: vi.fn()
        },
        addEventListener: vi.fn((event, handler) => {
          if (event === 'load') {
            // Store the load handler to call it later
            mockXHR._loadHandler = handler
          }
        }),
        status: 200,
        responseText: JSON.stringify({ success: true, fileId: 123 }),
        withCredentials: false
      }

      // Mock XMLHttpRequest constructor
      const OriginalXHR = global.XMLHttpRequest
      global.XMLHttpRequest = function() {
        return mockXHR
      }

      const progressCallback = vi.fn()

      // Trigger success after send
      mockXHR.send.mockImplementation(() => {
        // Simulate immediate load event
        if (mockXHR._loadHandler) {
          mockXHR._loadHandler()
        }
      })

      const result = await client.uploadFile('/api/upload', mockFile, progressCallback)

      expect(mockXHR.open).toHaveBeenCalledWith('POST', 'http://localhost:8000/api/upload')
      expect(mockXHR.send).toHaveBeenCalled()
      expect(result.data.success).toBe(true)

      // Restore original
      global.XMLHttpRequest = OriginalXHR
    })
  })

  describe('Timeout Handling', () => {
    it('should abort request on timeout', async () => {
      // Create a controller that will be aborted
      const abortError = new Error('The operation was aborted')
      abortError.name = 'AbortError'

      global.fetch.mockImplementation(() =>
        new Promise((resolve, reject) => {
          // Simulate a request that would be aborted
          setTimeout(() => reject(abortError), 100)
        })
      )

      // Use a very short timeout
      await expect(
        client.get('/api/slow', { timeout: 50, retries: 0 })
      ).rejects.toThrow()
    })
  })
})
