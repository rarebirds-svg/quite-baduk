// 방문 비콘이 경로당 1회 전송되고 앱셸에서 비활성인지 검증.
import { render } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ usePathname: () => "/glossary/sahwal" }));
vi.mock("@/lib/appShell", () => ({ IS_APP_SHELL: false }));

import VisitBeacon from "@/components/VisitBeacon";

describe("VisitBeacon", () => {
  beforeEach(() => {
    (navigator as unknown as { sendBeacon: unknown }).sendBeacon = vi.fn();
  });

  it("경로당 1회 전송", () => {
    render(<VisitBeacon />);
    expect(navigator.sendBeacon).toHaveBeenCalledTimes(1);
    const [url] = (navigator.sendBeacon as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toBe("/api/analytics/hit");
  });
});
