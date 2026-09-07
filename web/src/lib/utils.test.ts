import { describe, expect, it } from "vitest";
import { formatMs, formatPct } from "./utils";

describe("formatters", () => {
  it("formats percents and latency", () => {
    expect(formatPct(94.2)).toBe("94.2%");
    expect(formatMs(48)).toBe("48ms");
    expect(formatMs(2400)).toBe("2.4s");
  });
});
