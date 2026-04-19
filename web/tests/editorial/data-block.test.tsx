import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { DataBlock } from "../../components/editorial/DataBlock";

describe("DataBlock", () => {
  it("renders label and value", () => {
    render(<DataBlock label="Move" value="47" />);
    expect(screen.getByText("Move")).toBeInTheDocument();
    expect(screen.getByText("47")).toBeInTheDocument();
  });

  it("renders optional description", () => {
    render(<DataBlock label="Time" value="4:22" description="left on clock" />);
    expect(screen.getByText("left on clock")).toBeInTheDocument();
  });

  it("accepts ReactNode as value for compound displays", () => {
    render(<DataBlock label="Capture" value={<span>● 3 ○ 2</span>} />);
    expect(screen.getByText("● 3 ○ 2")).toBeInTheDocument();
  });
});
