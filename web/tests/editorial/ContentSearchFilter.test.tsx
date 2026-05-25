// 검색·초성 필터 동작 테스트.
import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ContentSearchFilter } from "../../components/editorial/ContentSearchFilter";

const ITEMS = [
  { slug: "bik", title: "빅", excerpt: "양쪽 돌이 살아 있는 상태." },
  { slug: "chuk", title: "축", excerpt: "직선으로 추격해 활로를 줄이는 기본 기술." },
  { slug: "dan-gup", title: "단·급", excerpt: "한국 바둑 실력 단위." },
];

describe("ContentSearchFilter", () => {
  it("renders all items by default", () => {
    render(
      <ContentSearchFilter
        items={ITEMS}
        searchPlaceholder="검색"
        filterAllLabel="전체"
        emptyLabel="없음"
        renderItem={(it) => <div key={it.slug}>{it.title}</div>}
      />,
    );
    expect(screen.getByText("빅")).toBeInTheDocument();
    expect(screen.getByText("축")).toBeInTheDocument();
    expect(screen.getByText("단·급")).toBeInTheDocument();
  });

  it("filters by search text (title)", () => {
    render(
      <ContentSearchFilter
        items={ITEMS}
        searchPlaceholder="검색"
        filterAllLabel="전체"
        emptyLabel="없음"
        renderItem={(it) => <div key={it.slug}>{it.title}</div>}
      />,
    );
    fireEvent.change(screen.getByPlaceholderText("검색"), { target: { value: "축" } });
    expect(screen.getByText("축")).toBeInTheDocument();
    expect(screen.queryByText("빅")).not.toBeInTheDocument();
  });

  it("filters by lead consonant chip", () => {
    render(
      <ContentSearchFilter
        items={ITEMS}
        searchPlaceholder="검색"
        filterAllLabel="전체"
        emptyLabel="없음"
        renderItem={(it) => <div key={it.slug}>{it.title}</div>}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "ㅊ" }));
    expect(screen.getByText("축")).toBeInTheDocument();
    expect(screen.queryByText("빅")).not.toBeInTheDocument();
  });

  it("shows emptyLabel when no items match", () => {
    render(
      <ContentSearchFilter
        items={ITEMS}
        searchPlaceholder="검색"
        filterAllLabel="전체"
        emptyLabel="없음"
        renderItem={(it) => <div key={it.slug}>{it.title}</div>}
      />,
    );
    fireEvent.change(screen.getByPlaceholderText("검색"), { target: { value: "zzz" } });
    expect(screen.getByText("없음")).toBeInTheDocument();
  });
});
