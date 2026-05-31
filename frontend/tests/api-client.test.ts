import { describe, expect, it } from "vitest";

import { apiClient } from "../lib/api/client";

describe("api client scaffold", () => {
  it("creates a typed client with health helpers", () => {
    expect(typeof apiClient.GET).toBe("function");
    expect(typeof apiClient.POST).toBe("function");
  });
});