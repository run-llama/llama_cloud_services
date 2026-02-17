import { describe, it, expect, vi } from "vitest";
import {
  isHeartbeatTimeoutError,
  retryOnHeartbeatTimeout,
} from "../src/temporal.js";

describe("Temporal Heartbeat Timeout Utilities", () => {
  describe("isHeartbeatTimeoutError", () => {
    it("should detect ActivityFailure wrapping TimeoutFailure with HEARTBEAT type (numeric)", () => {
      const error = {
        name: "ActivityFailure",
        message: "activity failed",
        cause: {
          name: "TimeoutFailure",
          message: "timeout",
          timeoutType: 4,
        },
      };
      expect(isHeartbeatTimeoutError(error)).toBe(true);
    });

    it("should detect ActivityFailure wrapping TimeoutFailure with HEARTBEAT type (string)", () => {
      const error = {
        name: "ActivityFailure",
        message: "activity failed",
        cause: {
          name: "TimeoutFailure",
          message: "timeout",
          timeoutType: "HEARTBEAT",
        },
      };
      expect(isHeartbeatTimeoutError(error)).toBe(true);
    });

    it("should detect ActivityError wrapping TimeoutError with HEARTBEAT type", () => {
      const error = {
        name: "ActivityError",
        message: "activity error",
        cause: {
          name: "TimeoutError",
          message: "timeout",
          timeoutType: 4,
        },
      };
      expect(isHeartbeatTimeoutError(error)).toBe(true);
    });

    it("should reject ActivityFailure with non-heartbeat timeout type", () => {
      const error = {
        name: "ActivityFailure",
        message: "activity failed",
        cause: {
          name: "TimeoutFailure",
          message: "timeout",
          timeoutType: 1, // START_TO_CLOSE
        },
      };
      expect(isHeartbeatTimeoutError(error)).toBe(false);
    });

    it("should reject ActivityFailure with non-timeout cause", () => {
      const error = {
        name: "ActivityFailure",
        message: "activity failed",
        cause: {
          name: "ApplicationFailure",
          message: "app error",
        },
      };
      expect(isHeartbeatTimeoutError(error)).toBe(false);
    });

    it("should detect heartbeat timeout from error message", () => {
      const error = new Error("activity Heartbeat timeout");
      expect(isHeartbeatTimeoutError(error)).toBe(true);
    });

    it("should detect heartbeat_timeout in error message", () => {
      const error = new Error("Failed due to heartbeat_timeout");
      expect(isHeartbeatTimeoutError(error)).toBe(true);
    });

    it("should reject non-heartbeat errors", () => {
      const error = new Error("Connection refused");
      expect(isHeartbeatTimeoutError(error)).toBe(false);
    });

    it("should handle null/undefined", () => {
      expect(isHeartbeatTimeoutError(null)).toBe(false);
      expect(isHeartbeatTimeoutError(undefined)).toBe(false);
    });

    it("should handle non-object errors", () => {
      expect(isHeartbeatTimeoutError("string error")).toBe(false);
      expect(isHeartbeatTimeoutError(42)).toBe(false);
    });
  });

  describe("retryOnHeartbeatTimeout", () => {
    it("should return result on success", async () => {
      const fn = vi.fn().mockResolvedValue("success");
      const result = await retryOnHeartbeatTimeout(fn);
      expect(result).toBe("success");
      expect(fn).toHaveBeenCalledTimes(1);
    });

    it("should retry on heartbeat timeout error", async () => {
      const heartbeatError = Object.assign(new Error("timeout"), {
        name: "ActivityFailure",
        cause: { name: "TimeoutFailure", timeoutType: 4 },
      });

      const fn = vi
        .fn()
        .mockRejectedValueOnce(heartbeatError)
        .mockResolvedValue("recovered");

      const result = await retryOnHeartbeatTimeout(fn, { maxRetries: 3 });
      expect(result).toBe("recovered");
      expect(fn).toHaveBeenCalledTimes(2);
    });

    it("should not retry on non-heartbeat errors", async () => {
      const appError = new Error("Application error");
      const fn = vi.fn().mockRejectedValue(appError);

      await expect(retryOnHeartbeatTimeout(fn)).rejects.toThrow(
        "Application error",
      );
      expect(fn).toHaveBeenCalledTimes(1);
    });

    it("should exhaust retries on persistent heartbeat timeout", async () => {
      const heartbeatError = Object.assign(new Error("timeout"), {
        name: "ActivityFailure",
        cause: { name: "TimeoutFailure", timeoutType: 4 },
      });

      const fn = vi.fn().mockRejectedValue(heartbeatError);

      await expect(
        retryOnHeartbeatTimeout(fn, { maxRetries: 2 }),
      ).rejects.toBe(heartbeatError);
      expect(fn).toHaveBeenCalledTimes(3); // initial + 2 retries
    });

    it("should call onRetry callback before each retry", async () => {
      const heartbeatError = Object.assign(new Error("timeout"), {
        name: "ActivityFailure",
        cause: { name: "TimeoutFailure", timeoutType: 4 },
      });

      const fn = vi
        .fn()
        .mockRejectedValueOnce(heartbeatError)
        .mockRejectedValueOnce(heartbeatError)
        .mockResolvedValue("ok");

      const onRetry = vi.fn();
      const result = await retryOnHeartbeatTimeout(fn, {
        maxRetries: 3,
        onRetry,
      });

      expect(result).toBe("ok");
      expect(onRetry).toHaveBeenCalledTimes(2);
      expect(onRetry).toHaveBeenCalledWith(1, heartbeatError);
      expect(onRetry).toHaveBeenCalledWith(2, heartbeatError);
    });

    it("should default to 3 retries", async () => {
      const heartbeatError = Object.assign(new Error("timeout"), {
        name: "ActivityFailure",
        cause: { name: "TimeoutFailure", timeoutType: 4 },
      });

      const fn = vi.fn().mockRejectedValue(heartbeatError);

      await expect(retryOnHeartbeatTimeout(fn)).rejects.toBe(heartbeatError);
      expect(fn).toHaveBeenCalledTimes(4); // initial + 3 retries
    });

    it("should detect heartbeat timeout from message and retry", async () => {
      const messageError = new Error("activity Heartbeat timeout");
      const fn = vi
        .fn()
        .mockRejectedValueOnce(messageError)
        .mockResolvedValue("recovered");

      const result = await retryOnHeartbeatTimeout(fn);
      expect(result).toBe("recovered");
      expect(fn).toHaveBeenCalledTimes(2);
    });
  });
});
