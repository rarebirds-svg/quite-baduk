import { describe, it, expect, vi, afterEach } from "vitest";
import { render } from "@testing-library/react";
import Board from "@/components/Board";
import { resolveMoveConfirm } from "@/store/movePrefStore";
import { withJosa } from "@/lib/hangul";

afterEach(() => vi.unstubAllGlobals());

describe("resolveMoveConfirm", () => {
  it("honours explicit preferences regardless of pointer type", () => {
    vi.stubGlobal("matchMedia", vi.fn().mockReturnValue({ matches: true }));
    expect(resolveMoveConfirm("tap")).toBe(false);
    expect(resolveMoveConfirm("confirm")).toBe(true);
  });

  it("auto follows (pointer: coarse)", () => {
    const mm = vi.fn().mockReturnValue({ matches: true });
    vi.stubGlobal("matchMedia", mm);
    expect(resolveMoveConfirm("auto")).toBe(true);
    expect(mm).toHaveBeenCalledWith("(pointer: coarse)");
    mm.mockReturnValue({ matches: false });
    expect(resolveMoveConfirm("auto")).toBe(false);
  });
});

describe("Board pending stone", () => {
  it("renders a ghost stone only when pendingMove is set", () => {
    const empty = ".".repeat(81);
    const { container, rerender } = render(<Board size={9} board={empty} />);
    expect(container.querySelector("[data-pending-move]")).toBeNull();
    rerender(<Board size={9} board={empty} pendingMove={{ x: 4, y: 4 }} pendingColor="W" />);
    const ghost = container.querySelector("[data-pending-move]");
    expect(ghost).not.toBeNull();
    // 가착수는 실제 돌(data-stone)로 세지 않는다.
    expect(container.querySelectorAll("[data-stone]")).toHaveLength(0);
  });
});

describe("withJosa", () => {
  it("picks the particle by final consonant", () => {
    expect(withJosa("이창호", "과", "와")).toBe("이창호와");
    expect(withJosa("조훈현", "과", "와")).toBe("조훈현과");
    expect(withJosa("Ke Jie", "과", "와")).toBe("Ke Jie와");
  });
});
