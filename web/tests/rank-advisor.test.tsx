import { describe, it, expect, vi } from "vitest";
import { render, fireEvent } from "@testing-library/react";
import RankAdvisor, { ADVISOR_PRESETS } from "@/components/RankAdvisor";

describe("RankAdvisor", () => {
  it("applies both the suggested rank and board size", () => {
    const onSelect = vi.fn();
    const { getByText } = render(<RankAdvisor onSelect={onSelect} />);
    fireEvent.click(getByText("급수를 모르겠어요?"));
    fireEvent.click(getByText("처음이에요"));
    // 결과 화면에 추천 판 크기가 같이 보인다.
    expect(getByText(/9×9/)).toBeTruthy();
    fireEvent.click(getByText("이 설정 적용"));
    expect(onSelect).toHaveBeenCalledWith("9k", 9);
    expect(ADVISOR_PRESETS.q1New).toEqual({ rank: "9k", boardSize: 9 });
  });

  it("routes experienced players to 19×19", () => {
    const onSelect = vi.fn();
    const { getByText } = render(<RankAdvisor onSelect={onSelect} />);
    fireEvent.click(getByText("급수를 모르겠어요?"));
    fireEvent.click(getByText("둬본 적 있어요"));
    fireEvent.click(getByText("유단자예요"));
    fireEvent.click(getByText("이 설정 적용"));
    expect(onSelect).toHaveBeenCalledWith("2d", 19);
  });
});
