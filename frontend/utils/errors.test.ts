import { describe, expect, it } from 'vitest'
import { describeHttpError, extractErrorMessage } from './errors'

describe('extractErrorMessage', () => {
  it('returns the fallback for falsy or unrecognized errors', () => {
    expect(extractErrorMessage(null)).toBe('Something went wrong')
    expect(extractErrorMessage(undefined, 'Boom')).toBe('Boom')
    expect(extractErrorMessage({}, 'Boom')).toBe('Boom')
  })

  it('maps 413 to a friendly file-size message regardless of body', () => {
    expect(extractErrorMessage({ response: { status: 413 } })).toBe(
      'The file is too large to upload. Please choose a smaller file.',
    )
    // Even with an unreadable HTML body from the proxy.
    expect(extractErrorMessage({ response: { status: 413, data: '<html>...' } })).toBe(
      'The file is too large to upload. Please choose a smaller file.',
    )
  })

  it('surfaces the correlation id from a global 500 payload', () => {
    expect(
      extractErrorMessage({ response: { data: { error_id: 'abc123', message: 'Boom' } } }),
    ).toBe('Boom (Error ID: abc123)')
    // No message → generic base, still carrying the id.
    expect(extractErrorMessage({ response: { data: { error_id: 'abc123' } } })).toBe(
      'An unexpected error occurred. (Error ID: abc123)',
    )
    // Id already present in the message → not duplicated.
    expect(
      extractErrorMessage({ response: { data: { error_id: 'abc123', message: 'Boom abc123' } } }),
    ).toBe('Boom abc123')
  })

  it('reads a plain string detail', () => {
    expect(extractErrorMessage({ response: { data: { detail: 'Not found' } } })).toBe('Not found')
  })

  it('reads a structured detail object, appending its error id', () => {
    expect(extractErrorMessage({ response: { data: { detail: { message: 'Conflict' } } } })).toBe(
      'Conflict',
    )
    expect(
      extractErrorMessage({
        response: { data: { detail: { message: 'Conflict', error_id: 'x1' } } },
      }),
    ).toBe('Conflict (Error ID: x1)')
  })

  it('localizes a structured detail carrying a known error code', () => {
    expect(
      extractErrorMessage({
        response: { data: { detail: { code: 'auth.invalid_credentials', message: 'ignored' } } },
      }),
    ).toBe('Incorrect email or password')
  })

  it('interpolates params for a localized error code', () => {
    // errors.http.bad_request uses {operation}/{detail}; reuse it as a
    // param-carrying code to prove params reach the catalog string.
    expect(
      extractErrorMessage({
        response: {
          data: {
            detail: {
              code: 'http.bad_request',
              params: { operation: 'Save', detail: 'oops' },
              message: 'ignored',
            },
          },
        },
      }),
    ).toBe('Save failed: oops')
  })

  it('falls back to the embedded message when the error code is unknown', () => {
    expect(
      extractErrorMessage({
        response: { data: { detail: { code: 'not.a.real.code', message: 'Plain English' } } },
      }),
    ).toBe('Plain English')
  })

  it('reads a top-level message when there is no detail', () => {
    expect(extractErrorMessage({ response: { data: { message: 'Just a message' } } })).toBe(
      'Just a message',
    )
  })

  it('reads the first msg of a FastAPI validation error list', () => {
    expect(
      extractErrorMessage({ response: { data: { detail: [{ msg: 'field required' }] } } }),
    ).toBe('field required')
  })

  it('falls back to err.message when there is no usable response body', () => {
    expect(extractErrorMessage({ message: 'Network Error' })).toBe('Network Error')
  })
})

describe('describeHttpError', () => {
  it('reports a network error when there is no response', () => {
    expect(describeHttpError({ message: 'Network Error' }, 'Loading trials')).toBe(
      'Network error during Loading trials. Please check your connection and try again.',
    )
  })

  it('maps common status codes to actionable messages', () => {
    expect(describeHttpError({ response: { status: 403 } }, 'Loading trials')).toBe(
      "Permission denied: You don't have access to loading trials.",
    )
    expect(describeHttpError({ response: { status: 404 } }, 'Loading trials')).toBe(
      'Resource not found during Loading trials. Please refresh and try again.',
    )
    expect(describeHttpError({ response: { status: 500 } }, 'Loading trials')).toBe(
      'Server error during Loading trials. Please try again later or contact support.',
    )
  })

  it('includes the extracted detail on a 400', () => {
    expect(
      describeHttpError({ response: { status: 400, data: { detail: 'bad input' } } }, 'Saving'),
    ).toBe('Saving failed: bad input')
  })
})
