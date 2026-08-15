// 랜딩 보드 프리뷰가 시작 폼으로 유도하는지 — 클릭 시 닉네임 입력 포커스를 검증한다.
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

import { BoardPreview } from "@/components/editorial/BoardPreview";
import QuickStartForm, { QUICK_START_INPUT_ID } from "@/components/QuickStartForm";
import { useAuthStore } from "@/store/authStore";

beforeEach(() => {
  useAuthStore.setState({ session: null, isAdmin: false });
  Element.prototype.scrollIntoView = vi.fn();
});

describe("BoardPreview", () => {
  it("클릭하면 시작 폼의 닉네임 입력으로 포커스가 간다", () => {
    render(
      <>
        <BoardPreview />
        <section id="start">
          <QuickStartForm />
        </section>
      </>
    );

    // 입력창은 autoFocus라 마운트 직후 포커스를 가진다 — 클릭이 실제로
    // 포커스를 되돌리는지 보기 위해 먼저 포커스를 뺀다.
    (document.activeElement as HTMLElement | null)?.blur();
    expect(document.activeElement?.id).not.toBe(QUICK_START_INPUT_ID);

    const trigger = screen.getByRole("button", { name: /이 판에서 시작하기/ });
    fireEvent.click(trigger);

    expect(document.activeElement?.id).toBe(QUICK_START_INPUT_ID);
  });
});
