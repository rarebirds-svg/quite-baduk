import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatFigure } from "../../components/editorial/StatFigure";

describe("StatFigure", () => {
  it("renders value with label", () => {
    render(<StatFigure value="62.3" unit="%" label="Win Rate" />);
    expect(screen.getByText("Win Rate")).toBeInTheDocument();
    expect(screen.getByText("62.3")).toBeInTheDocument();
    expect(screen.getByText("%")).toBeInTheDocument();
  });

  it("applies font-mono to value element", () => {
    const { container } = render(<StatFigure value="47" label="Move" />);
    const val = container.querySelector("[data-stat-value]");
    expect(val?.className).toMatch(/font-mono/);
  });

  it("accepts numeric value and renders as string", () => {
    render(<StatFigure value={100} label="Score" />);
    expect(screen.getByText("100")).toBeInTheDocument();
  });
});
