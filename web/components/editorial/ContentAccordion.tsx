"use client";
// FAQ 단일 펼침 accordion — URL hash로 마운트 시 자동 펼침 + scroll.
import * as React from "react";

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

export interface AccordionContentItem {
  slug: string;
  title: string;
  html: string;
}

export interface ContentAccordionProps {
  items: AccordionContentItem[];
}

export function ContentAccordion({ items }: ContentAccordionProps) {
  const [openSlug, setOpenSlug] = React.useState<string | undefined>(undefined);

  React.useEffect(() => {
    if (typeof window === "undefined") return;
    const hash = window.location.hash.replace(/^#/, "");
    if (!hash) return;
    if (items.some((it) => it.slug === hash)) {
      setOpenSlug(hash);
      requestAnimationFrame(() => {
        const el = document.getElementById(`faq-${hash}`);
        el?.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    }
  }, [items]);

  return (
    <Accordion
      type="single"
      collapsible
      value={openSlug}
      onValueChange={(v) => setOpenSlug(v || undefined)}
    >
      {items.map((it) => (
        <AccordionItem key={it.slug} value={it.slug} id={`faq-${it.slug}`}>
          <AccordionTrigger>{it.title}</AccordionTrigger>
          <AccordionContent>
            <div className="editorial-prose" dangerouslySetInnerHTML={{ __html: it.html }} />
          </AccordionContent>
        </AccordionItem>
      ))}
    </Accordion>
  );
}
