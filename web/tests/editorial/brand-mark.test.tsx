import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { BrandMark } from "../../components/editorial/BrandMark";

describe("BrandMark", () => {
  it("renders an SVG with aria-label", () => {
    const { container } = render(<BrandMark />);
    const svg = container.querySelector("svg");
    expect(svg).toHaveAttribute("aria-label", "Baduk");
    expect(svg).toHaveAttribute("width", "20");
  });

  it("accepts custom size", () => {
    const { container } = render(<BrandMark size={32} />);
    expect(container.querySelector("svg")).toHaveAttribute("width", "32");
  });
});
