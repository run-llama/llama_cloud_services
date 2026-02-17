/**
 * Utilities for retrying LlamaParse activities in Temporal
 * specifically when they fail due to activity heartbeat timeout.
 *
 * These utilities detect Temporal's ActivityFailure wrapping a TimeoutFailure
 * with timeoutType HEARTBEAT, without requiring a direct dependency on the
 * Temporal SDK.
 *
 * Usage in a Temporal workflow:
 *
 * ```ts
 * import { retryOnHeartbeatTimeout } from 'llama-cloud-services/temporal';
 * import { proxyActivities } from '@temporalio/workflow';
 *
 * const { llamaParse } = proxyActivities<typeof activities>({
 *   startToCloseTimeout: '30m',
 *   heartbeatTimeout: '60s',
 *   retry: { maximumAttempts: 1 }, // disable built-in retry
 * });
 *
 * export async function parseWorkflow(input: ParseInput): Promise<ParseResult> {
 *   return retryOnHeartbeatTimeout(() => llamaParse(input), { maxRetries: 3 });
 * }
 * ```
 */

// Temporal TimeoutType enum value for HEARTBEAT (from @temporalio/common proto)
const TIMEOUT_TYPE_HEARTBEAT = 4;

/**
 * Checks if an error is a Temporal activity heartbeat timeout error.
 *
 * Detects both the structured Temporal error types (ActivityFailure wrapping
 * TimeoutFailure with timeoutType HEARTBEAT) and fallback string matching
 * on the error message.
 */
export function isHeartbeatTimeoutError(error: unknown): boolean {
  if (!error || typeof error !== "object") return false;

  const err = error as Record<string, unknown>;

  // Check for Temporal's ActivityFailure → TimeoutFailure chain
  if (err.name === "ActivityFailure" || err.name === "ActivityError") {
    const cause =
      (err.cause as Record<string, unknown>) ??
      ((error as { __cause__?: unknown }).__cause__ as Record<string, unknown>);

    if (cause && typeof cause === "object") {
      const causeName = (cause as Record<string, unknown>).name;
      if (causeName === "TimeoutFailure" || causeName === "TimeoutError") {
        const timeoutType = (cause as Record<string, unknown>).timeoutType;
        return (
          timeoutType === TIMEOUT_TYPE_HEARTBEAT ||
          timeoutType === "HEARTBEAT" ||
          timeoutType === "TimeoutType.HEARTBEAT"
        );
      }
    }
  }

  // Fallback: match on error message
  const message = String(
    (err as { message?: string }).message ?? String(err),
  ).toLowerCase();
  return (
    message.includes("heartbeat timeout") ||
    message.includes("heartbeat_timeout")
  );
}

export interface RetryOnHeartbeatTimeoutOptions {
  /** Maximum number of retry attempts after the initial try (default: 3). */
  maxRetries?: number;
  /** Optional callback invoked before each retry with the attempt number and error. */
  onRetry?: (attempt: number, error: unknown) => void;
}

/**
 * Retries an async function only when it fails with a heartbeat timeout error.
 * All other errors are thrown immediately without retry.
 *
 * Designed for use in Temporal workflows to wrap activity calls so that
 * transient heartbeat timeouts (e.g. from SIGTERM, event-loop blocking)
 * are automatically retried while genuine failures propagate immediately.
 *
 * @param fn - The async function to execute (typically a Temporal activity call)
 * @param options - Retry configuration
 * @returns The result of the function
 */
export async function retryOnHeartbeatTimeout<T>(
  fn: () => Promise<T>,
  options: RetryOnHeartbeatTimeoutOptions = {},
): Promise<T> {
  const { maxRetries = 3, onRetry } = options;
  let lastError: unknown;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (err) {
      lastError = err;
      if (isHeartbeatTimeoutError(err) && attempt < maxRetries) {
        onRetry?.(attempt + 1, err);
        continue;
      }
      throw err;
    }
  }

  throw lastError;
}
