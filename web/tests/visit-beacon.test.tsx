// 방문 비콘이 경로당 1회 전송되고 앱셸에서 비활성인지 검증.
import { render } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ usePathname: () => "/glossary/sahwal" }));
vi.mock("@/lib/appShell", () => ({ IS_APP_SHELL: false }));

import VisitBeacon, { isPublicPath } from "@/components/VisitBeacon";

describe("VisitBeacon", () => {
  beforeEach(() => {
    (navigator as unknown as { sendBeacon: unknown }).sendBeacon = vi.fn();
  });

  it("공개 경로에서 1회 전송", () => {
    render(<VisitBeacon />);
    expect(navigator.sendBeacon).toHaveBeenCalledTimes(1);
    const [url] = (navigator.sendBeacon as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toBe("/api/analytics/hit");
  });
});

describe("isPublicPath", () => {
  it.each([
    ["/glossary/sahwal", true],
    ["/faq", true],
    ["/spectate/pro/1", true],
    ["/", true],
    ["/admin", false],
    ["/admin/analytics", false],
    ["/game/new", false],
    ["/daily", false],
    ["/spectate/watch", false],
  ])("%s → %s", (path, expected) => {
    expect(isPublicPath(path as string)).toBe(expected);
  });
});
