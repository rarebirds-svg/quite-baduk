import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MoveList, type MoveEntry } from "../../components/editorial/MoveList";

const moves: MoveEntry[] = [
  { number: 1, color: "B", coord: "E5" },
  { number: 2, color: "W", coord: "C3" },
  { number: 3, color: "B", coord: "pass" },
];

describe("MoveList", () => {
  it("renders all move rows", () => {
    render(<MoveList moves={moves} currentIndex={0} />);
    expect(screen.getByText("1")).toBeInTheDocument();
    expect(screen.getByText("E5")).toBeInTheDocument();
    expect(screen.getByText("C3")).toBeInTheDocument();
  });

  it("highlights the current move", () => {
    const { container } = render(<MoveList moves={moves} currentIndex={1} />);
    const active = container.querySelector('[data-current="true"]');
    expect(active?.textContent).toContain("C3");
  });

  it("renders pass as italic label", () => {
    render(<MoveList moves={moves} currentIndex={2} />);
    const passCell = screen.getByText("pass");
    expect(passCell.tagName.toLowerCase()).toBe("em");
  });

  it("fires onSelect when a move is clicked", async () => {
    const { default: userEvent } = await import("@testing-library/user-event");
    const user = userEvent.setup();
    let picked = -1;
    render(
      <MoveList moves={moves} currentIndex={0} onSelect={(i) => (picked = i)} />
    );
    await user.click(screen.getByText("C3"));
    expect(picked).toBe(1);
  });
});
