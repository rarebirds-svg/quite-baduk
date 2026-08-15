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
      "/daily",
      "/spectate",
      "/spectate/789",
      "/spectate/watch",
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
    ]) {
      expect(isPublicPath(p)).toBe(false);
    }
  });

  it("does not let a prefix match leak a sibling path", () => {
    // Prefix matching is segment-aware: "/daily" must not make
    // "/dailyreport" public, nor "/spectate" make "/spectatex" public.
    expect(isPublicPath("/dailyreport")).toBe(false);
    expect(isPublicPath("/spectatex")).toBe(false);
    expect(isPublicPath("/glossaryx")).toBe(false);
  });
});
