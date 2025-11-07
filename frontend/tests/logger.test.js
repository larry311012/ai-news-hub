import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { Logger } from '../utils/logger.js'

describe('Logger Utility', () => {
  let consoleLogSpy
  let consoleDebugSpy
  let consoleInfoSpy
  let consoleWarnSpy
  let consoleErrorSpy

  beforeEach(() => {
    consoleLogSpy = vi.spyOn(console, 'log').mockImplementation()
    consoleDebugSpy = vi.spyOn(console, 'debug').mockImplementation()
    consoleInfoSpy = vi.spyOn(console, 'info').mockImplementation()
    consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation()
    consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Logger Creation', () => {
    it('should create logger without namespace', () => {
      const logger = new Logger()
      expect(logger).toBeDefined()
      expect(logger.namespace).toBe('')
    })

    it('should create logger with namespace', () => {
      const logger = new Logger('TestModule')
      expect(logger.namespace).toBe('TestModule')
    })

    it('should detect development environment', () => {
      const logger = new Logger()
      expect(logger.isDev).toBe(true) // Based on test environment
    })
  })

  describe('Development Mode Logging', () => {
    it('should output info logs', () => {
      const logger = new Logger()
      logger.info('Info message', { data: 'test' })

      expect(consoleInfoSpy).toHaveBeenCalled()
      expect(consoleInfoSpy.mock.calls[0]).toContain('Info message')
    })

    it('should output warn logs', () => {
      const logger = new Logger()
      logger.warn('Warning message')

      expect(consoleWarnSpy).toHaveBeenCalled()
      expect(consoleWarnSpy.mock.calls[0]).toContain('Warning message')
    })

    it('should output error logs', () => {
      const logger = new Logger()
      logger.error('Error message')

      expect(consoleErrorSpy).toHaveBeenCalled()
      expect(consoleErrorSpy.mock.calls[0]).toContain('Error message')
    })

    it('should include namespace in logs', () => {
      const logger = new Logger('TestModule')
      logger.info('Test message')

      expect(consoleInfoSpy).toHaveBeenCalled()
      const firstArg = consoleInfoSpy.mock.calls[0][0]
      expect(firstArg).toContain('[TestModule]')
    })
  })

  describe('Log Level Methods', () => {
    it('should support multiple arguments', () => {
      const logger = new Logger()
      logger.info('Message', { key: 'value' }, 123, true)

      expect(consoleInfoSpy).toHaveBeenCalledWith(
        expect.any(String),
        'Message',
        { key: 'value' },
        123,
        true
      )
    })

    it('should handle objects in log messages', () => {
      const logger = new Logger()
      const testObj = { name: 'test', value: 42 }
      logger.info('Object:', testObj)

      expect(consoleInfoSpy).toHaveBeenCalledWith(
        expect.any(String),
        'Object:',
        testObj
      )
    })

    it('should handle arrays in log messages', () => {
      const logger = new Logger()
      const testArray = [1, 2, 3]
      logger.warn('Array:', testArray)

      expect(consoleWarnSpy).toHaveBeenCalledWith(
        expect.any(String),
        'Array:',
        testArray
      )
    })
  })

  describe('Console Table', () => {
    it('should call console.table in development', () => {
      const logger = new Logger()
      const tableData = [
        { name: 'Alice', age: 30 },
        { name: 'Bob', age: 25 }
      ]

      const tableSpy = vi.spyOn(console, 'table').mockImplementation()
      logger.table(tableData)

      if (logger.isDev) {
        expect(tableSpy).toHaveBeenCalledWith(tableData)
      }

      tableSpy.mockRestore()
    })
  })

  describe('Console Groups', () => {
    it('should support grouping logs', () => {
      const logger = new Logger()
      const groupSpy = vi.spyOn(console, 'group').mockImplementation()
      const groupEndSpy = vi.spyOn(console, 'groupEnd').mockImplementation()

      logger.group('Test Group')
      logger.info('Inside group')
      logger.groupEnd()

      if (logger.isDev) {
        expect(groupSpy).toHaveBeenCalledWith('Test Group')
        expect(groupEndSpy).toHaveBeenCalled()
      }

      groupSpy.mockRestore()
      groupEndSpy.mockRestore()
    })
  })

  describe('Performance Timing', () => {
    it('should support time and timeEnd', () => {
      const logger = new Logger()
      const timeSpy = vi.spyOn(console, 'time').mockImplementation()
      const timeEndSpy = vi.spyOn(console, 'timeEnd').mockImplementation()

      logger.time('operation')
      logger.timeEnd('operation')

      if (logger.isDev) {
        expect(timeSpy).toHaveBeenCalledWith('operation')
        expect(timeEndSpy).toHaveBeenCalledWith('operation')
      }

      timeSpy.mockRestore()
      timeEndSpy.mockRestore()
    })
  })

  describe('Global Availability', () => {
    it('should be available on window object', () => {
      expect(window.Logger).toBe(Logger)
      expect(window.logger).toBeDefined()
    })
  })

  describe('Edge Cases', () => {
    it('should handle undefined arguments', () => {
      const logger = new Logger()
      expect(() => logger.info(undefined)).not.toThrow()
    })

    it('should handle null arguments', () => {
      const logger = new Logger()
      expect(() => logger.warn(null)).not.toThrow()
    })

    it('should handle empty strings', () => {
      const logger = new Logger()
      logger.error('')
      expect(consoleErrorSpy).toHaveBeenCalled()
    })
  })
})
