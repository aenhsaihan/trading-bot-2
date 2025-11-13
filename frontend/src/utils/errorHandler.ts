/**
 * Centralized error handling utility for API calls
 * 
 * Provides:
 * - Network error detection and handling
 * - API error response parsing
 * - Retry logic for transient failures
 * - User-friendly error messages
 */

export interface ApiError {
  message: string;
  statusCode?: number;
  isNetworkError: boolean;
  isRetryable: boolean;
  originalError?: Error;
}

export interface RetryOptions {
  maxRetries?: number;
  retryDelay?: number;
  retryableStatusCodes?: number[];
}

const DEFAULT_RETRY_OPTIONS: Required<RetryOptions> = {
  maxRetries: 3,
  retryDelay: 1000, // 1 second
  retryableStatusCodes: [408, 429, 500, 502, 503, 504], // Request timeout, rate limit, server errors
};

/**
 * Check if an error is a network error (no response from server)
 */
export function isNetworkError(error: unknown): boolean {
  if (error instanceof TypeError && error.message.includes('fetch')) {
    return true;
  }
  if (error instanceof Error) {
    return (
      error.message.includes('NetworkError') ||
      error.message.includes('Failed to fetch') ||
      error.message.includes('Network request failed')
    );
  }
  return false;
}

/**
 * Check if an HTTP status code indicates a retryable error
 */
export function isRetryableStatusCode(statusCode: number): boolean {
  return DEFAULT_RETRY_OPTIONS.retryableStatusCodes.includes(statusCode);
}

/**
 * Parse error response from API
 * Handles both FastAPI validation errors and custom error messages
 */
export async function parseApiError(response: Response): Promise<string> {
  try {
    const errorData = await response.json();
    
    // FastAPI validation errors
    if (errorData.detail) {
      if (Array.isArray(errorData.detail)) {
        // Validation error array
        return errorData.detail
          .map((e: any) => {
            const field = e.loc ? e.loc.join('.') : e.field || 'unknown';
            return `${field}: ${e.msg || e.message}`;
          })
          .join(', ');
      } else {
        // Single error message
        return errorData.detail;
      }
    }
    
    // Generic error message
    if (errorData.message) {
      return errorData.message;
    }
    
    // Fallback to status text
    return response.statusText || `HTTP ${response.status}`;
  } catch {
    // If we can't parse JSON, return status text
    return response.statusText || `HTTP ${response.status}`;
  }
}

/**
 * Get user-friendly error message based on error type
 */
export function getUserFriendlyErrorMessage(error: ApiError): string {
  if (error.isNetworkError) {
    return 'Network error: Unable to connect to the server. Please check your internet connection.';
  }
  
  if (error.statusCode === 401) {
    return 'Authentication required. Please log in.';
  }
  
  if (error.statusCode === 403) {
    return 'Access denied. You do not have permission to perform this action.';
  }
  
  if (error.statusCode === 404) {
    return 'Resource not found. It may have been deleted or moved.';
  }
  
  if (error.statusCode === 408 || error.statusCode === 504) {
    return 'Request timeout. The server took too long to respond. Please try again.';
  }
  
  if (error.statusCode === 429) {
    return 'Too many requests. Please wait a moment and try again.';
  }
  
  if (error.statusCode && error.statusCode >= 500) {
    return 'Server error. Please try again later or contact support if the problem persists.';
  }
  
  // Return the original message if we have one
  return error.message || 'An unexpected error occurred.';
}

/**
 * Create a standardized API error object
 */
export async function createApiError(
  error: unknown,
  response?: Response
): Promise<ApiError> {
  const networkError = isNetworkError(error);
  
  if (networkError) {
    return {
      message: 'Network request failed',
      isNetworkError: true,
      isRetryable: true,
      originalError: error instanceof Error ? error : new Error(String(error)),
    };
  }
  
  if (response) {
    const message = await parseApiError(response);
    const statusCode = response.status;
    const retryable = isRetryableStatusCode(statusCode);
    
    return {
      message,
      statusCode,
      isNetworkError: false,
      isRetryable: retryable,
    };
  }
  
  // Generic error
  const message = error instanceof Error ? error.message : String(error);
  return {
    message,
    isNetworkError: false,
    isRetryable: false,
    originalError: error instanceof Error ? error : new Error(String(error)),
  };
}

/**
 * Sleep utility for retry delays
 */
function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Execute a fetch request with retry logic
 * 
 * @param fetchFn Function that returns a Promise<Response>
 * @param options Retry configuration
 * @returns Response from successful request
 * @throws ApiError if all retries fail
 */
export async function fetchWithRetry(
  fetchFn: () => Promise<Response>,
  options: RetryOptions = {}
): Promise<Response> {
  const config = { ...DEFAULT_RETRY_OPTIONS, ...options };
  let lastError: ApiError | null = null;
  
  for (let attempt = 0; attempt <= config.maxRetries; attempt++) {
    try {
      const response = await fetchFn();
      
      // If successful, return immediately
      if (response.ok) {
        return response;
      }
      
      // Check if error is retryable
      const apiError = await createApiError(null, response);
      if (!apiError.isRetryable || attempt === config.maxRetries) {
        throw apiError;
      }
      
      lastError = apiError;
      
      // Wait before retrying (exponential backoff)
      const delay = config.retryDelay * Math.pow(2, attempt);
      await sleep(delay);
      
    } catch (error) {
      const apiError = await createApiError(error);
      
      // Network errors are always retryable
      if (apiError.isNetworkError && attempt < config.maxRetries) {
        lastError = apiError;
        const delay = config.retryDelay * Math.pow(2, attempt);
        await sleep(delay);
        continue;
      }
      
      // Non-retryable error or max retries reached
      throw apiError;
    }
  }
  
  // Should never reach here, but TypeScript needs it
  throw lastError || new Error('Unknown error occurred');
}

/**
 * Handle API errors and return user-friendly messages
 * 
 * @param error The error to handle
 * @param defaultMessage Default message if error can't be parsed
 * @returns User-friendly error message
 */
export async function handleApiError(
  error: unknown,
  defaultMessage: string = 'An error occurred'
): Promise<string> {
  try {
    const apiError = await createApiError(error);
    return getUserFriendlyErrorMessage(apiError);
  } catch {
    return error instanceof Error ? error.message : defaultMessage;
  }
}

/**
 * Check if the backend API is reachable
 */
export async function checkApiHealth(baseUrl: string): Promise<boolean> {
  try {
    const response = await fetch(`${baseUrl}/health`, {
      method: 'GET',
      signal: AbortSignal.timeout(5000), // 5 second timeout
    });
    return response.ok;
  } catch {
    return false;
  }
}

