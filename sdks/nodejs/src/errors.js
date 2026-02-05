/**
 * Custom errors for CSV2GEO SDK
 */

/**
 * Base error class for CSV2GEO SDK
 */
class CSV2GEOError extends Error {
  constructor(message, code = null, status = null) {
    super(message);
    this.name = 'CSV2GEOError';
    this.code = code;
    this.status = status;
  }
}

/**
 * Raised when API key is missing, invalid, or revoked
 */
class AuthenticationError extends CSV2GEOError {
  constructor(message, code = null, status = 401) {
    super(message, code, status);
    this.name = 'AuthenticationError';
  }
}

/**
 * Raised when rate limit is exceeded
 */
class RateLimitError extends CSV2GEOError {
  constructor(message, code = null, status = 429, retryAfter = null) {
    super(message, code, status);
    this.name = 'RateLimitError';
    this.retryAfter = retryAfter;
  }
}

/**
 * Raised when request parameters are invalid
 */
class InvalidRequestError extends CSV2GEOError {
  constructor(message, code = null, status = 400) {
    super(message, code, status);
    this.name = 'InvalidRequestError';
  }
}

/**
 * Raised when API key lacks required permission
 */
class PermissionError extends CSV2GEOError {
  constructor(message, code = null, status = 403) {
    super(message, code, status);
    this.name = 'PermissionError';
  }
}

/**
 * Raised for general API errors
 */
class APIError extends CSV2GEOError {
  constructor(message, code = null, status = 500) {
    super(message, code, status);
    this.name = 'APIError';
  }
}

module.exports = {
  CSV2GEOError,
  AuthenticationError,
  RateLimitError,
  InvalidRequestError,
  PermissionError,
  APIError,
};
