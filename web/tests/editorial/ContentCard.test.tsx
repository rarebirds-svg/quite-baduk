// ContentCard 렌더 테스트.
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ContentCard } from "../../components/editorial/ContentCard";

describe("ContentCard", () => {
  const item = {
    href: "/glossary/chuk",
    title: "축",
    slug: "chuk",
    excerpt: "직선으로 추격하면서 활로를 줄여 잡는 기본 기술.",
    ctaLabel: "자세히 →",
  };

  it("renders title, slug, excerpt, and cta", () => {
    render(<ContentCard {...item} />);
    expect(screen.getByText("축")).toBeInTheDocument();
    expect(screen.getByText("CHUK")).toBeInTheDocument();
    expect(screen.getByText(item.excerpt)).toBeInTheDocument();
    expect(screen.getByText(item.ctaLabel)).toBeInTheDocument();
  });

  it("wraps the whole card in a Link to href", () => {
    render(<ContentCard {...item} />);
    const link = screen.getByRole("link", { name: /축/ });
    expect(link).toHaveAttribute("href", "/glossary/chuk");
  });
});
