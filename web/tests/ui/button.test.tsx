import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Button } from "../../components/ui/button";

describe("Button", () => {
  it("renders with default variant", () => {
    render(<Button>Click me</Button>);
    const btn = screen.getByRole("button", { name: "Click me" });
    expect(btn).toBeInTheDocument();
    expect(btn.className).toMatch(/bg-ink/);
  });

  it("applies outline variant classes", () => {
    render(<Button variant="outline">Outline</Button>);
    expect(screen.getByRole("button").className).toMatch(/border-ink/);
  });

  it("forwards ref", () => {
    let ref: HTMLButtonElement | null = null;
    render(<Button ref={(r) => { ref = r; }}>X</Button>);
    expect(ref).toBeInstanceOf(HTMLButtonElement);
  });
});
