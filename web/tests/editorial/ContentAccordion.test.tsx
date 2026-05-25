// FAQ accordion 동작 테스트.
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ContentAccordion } from "../../components/editorial/ContentAccordion";

const ITEMS = [
  { slug: "q1", title: "첫 질문?", html: "<p>첫 답변.</p>" },
  { slug: "q2", title: "두 번째 질문?", html: "<p>두 번째 답변.</p>" },
];

describe("ContentAccordion", () => {
  it("renders all question triggers", () => {
    render(<ContentAccordion items={ITEMS} />);
    expect(screen.getByText("첫 질문?")).toBeInTheDocument();
    expect(screen.getByText("두 번째 질문?")).toBeInTheDocument();
  });

  it("uses slug as accordion item value", () => {
    const { container } = render(<ContentAccordion items={ITEMS} />);
    expect(container.querySelector('[data-radix-collection-item]')).toBeTruthy();
  });
});
