import { describe, expect, it } from "vitest";

import { cn } from "../lib/utils";

describe("cn (Tailwind class merger)", () => {
  it("joins string args", () => {
    expect(cn("a", "b")).toBe("a b");
  });

  it("honours falsy + conditional classes via clsx", () => {
    expect(cn("a", false && "b", null, undefined, "c")).toBe("a c");
  });

  it("resolves Tailwind conflicts using tailwind-merge", () => {
    // px-2 vs px-4: tailwind-merge keeps the later utility.
    expect(cn("px-2", "px-4")).toBe("px-4");
  });

  it("preserves non-conflicting Tailwind utilities (order may shift but content is preserved)", () => {
    // tailwind-merge keeps all non-conflicting utilities; ordering is an
    // internal detail, so assert the content set rather than a literal string.
    const merged = cn("text-sm font-bold", "text-foreground").split(" ").sort();
    expect(merged).toEqual(["font-bold", "text-foreground", "text-sm"]);
  });
});
