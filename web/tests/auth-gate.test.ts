// AuthGate 공개/보호 경로 매트릭스 회귀 테스트 — 인증 우회 경계를 잠근다.
import { describe, expect, it } from "vitest";

import { isPublicPath } from "@/components/AuthGate";

describe("isPublicPath", () => {
  it("treats marketing and legal pages as public", () => {
    for (const p of ["/", "/privacy", "/terms", "/support", "/supporters"]) {
      expect(isPublicPath(p)).toBe(true);
    }
  });

  it("treats content (SEO) routes and their sub-paths as public", () => {
    for (const p of [
      "/glossary",
      "/glossary/dansu",
      "/faq",
      "/faq/ai-strength-levels",
      "/spectate/pro",
      "/spectate/pro/123",
      "/spectate/themes",
      "/spectate/themes/joseki",
      "/spectate/picks",
      "/spectate/picks/monthly/202605",
    ]) {
      expect(isPublicPath(p)).toBe(true);
    }
  });

  it("keeps interactive and admin areas session-gated", () => {
    for (const p of [
      "/game",
      "/game/play/42",
      "/admin",
      "/admin/sessions",
      "/settings",
      "/history",
      "/spectate", // live-spectate hub
      "/spectate/789", // a live game, not pro content
    ]) {
      expect(isPublicPath(p)).toBe(false);
    }
  });

  it("does not let a prefix match leak a sibling path", () => {
    // "/spectate/pro" must not make "/spectate/promotions" public.
    expect(isPublicPath("/spectate/promotions")).toBe(false);
    expect(isPublicPath("/glossaryx")).toBe(false);
  });
});
