// @vitest-environment jsdom

import { describe, expect, it } from "vitest";

import { PacketLoadError, isNonRetryableStatus } from "../lib/usePacket";

/**
 * Pinning the retry predicate that ships in app/providers.tsx.
 *
 * Re-declared here (not exported from providers.tsx because the predicate is
 * a closure over QueryClient state). Keep in sync with that file.
 */
function shouldRetry(failureCount: number, error: unknown): boolean {
  if (error instanceof PacketLoadError && isNonRetryableStatus(error.diag.status)) {
    return false;
  }
  return failureCount < 3;
}

describe("QueryClient retry predicate (#90 — no spinner-of-doom on 401)", () => {
  it("does NOT retry 4xx packet errors (auth / not-found / validation)", () => {
    for (const status of [400, 401, 403, 404, 422]) {
      const err = new PacketLoadError({
        status,
        body: null,
        url: "x",
        elapsedMs: 1,
      });
      expect(shouldRetry(0, err)).toBe(false);
    }
  });

  it("DOES retry 5xx packet errors (transient backend failures)", () => {
    for (const status of [500, 502, 503, 504]) {
      const err = new PacketLoadError({
        status,
        body: null,
        url: "x",
        elapsedMs: 1,
      });
      expect(shouldRetry(0, err)).toBe(true);
    }
  });

  it("DOES retry packet errors with no response (network / CORS)", () => {
    const err = new PacketLoadError({
      status: undefined,
      body: null,
      url: "",
      elapsedMs: 30000,
    });
    expect(shouldRetry(0, err)).toBe(true);
  });

  it("stops retrying after the default 3-retry budget for retryable errors", () => {
    const err = new PacketLoadError({
      status: 503,
      body: null,
      url: "x",
      elapsedMs: 1,
    });
    expect(shouldRetry(2, err)).toBe(true);
    expect(shouldRetry(3, err)).toBe(false);
  });

  it("keeps default retry behaviour for non-PacketLoadError errors", () => {
    const generic = new Error("Some other failure");
    expect(shouldRetry(0, generic)).toBe(true);
    expect(shouldRetry(2, generic)).toBe(true);
    expect(shouldRetry(3, generic)).toBe(false);
  });
});

describe("isNonRetryableStatus", () => {
  it("is true for the 4xx range", () => {
    expect(isNonRetryableStatus(400)).toBe(true);
    expect(isNonRetryableStatus(499)).toBe(true);
  });

  it("is false for 5xx, 3xx, 2xx, and undefined", () => {
    expect(isNonRetryableStatus(500)).toBe(false);
    expect(isNonRetryableStatus(304)).toBe(false);
    expect(isNonRetryableStatus(200)).toBe(false);
    expect(isNonRetryableStatus(undefined)).toBe(false);
  });
});
