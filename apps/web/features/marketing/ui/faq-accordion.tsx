"use client";

import * as React from "react";

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/shared/ui/navigation";

export type FaqItem = {
  id: string;
  question: string;
  answer: React.ReactNode;
};

type FaqAccordionProps = {
  items: readonly FaqItem[];
};

function hashToValue(items: readonly FaqItem[]): string | undefined {
  if (typeof window === "undefined") return undefined;
  const hash = window.location.hash.replace(/^#/, "");
  if (!hash) return undefined;
  return items.some((item) => item.id === hash) ? hash : undefined;
}

export function FaqAccordion({ items }: FaqAccordionProps) {
  const [value, setValue] = React.useState<string | undefined>(undefined);

  React.useEffect(() => {
    const apply = () => setValue(hashToValue(items));
    apply();
    window.addEventListener("hashchange", apply);
    return () => window.removeEventListener("hashchange", apply);
  }, [items]);

  return (
    <Accordion
      type="single"
      collapsible
      className="w-full"
      value={value}
      onValueChange={setValue}
    >
      {items.map((item) => (
        <AccordionItem key={item.id} value={item.id} id={item.id} className="scroll-mt-24">
          <AccordionTrigger className="text-base">{item.question}</AccordionTrigger>
          <AccordionContent className="leading-relaxed">{item.answer}</AccordionContent>
        </AccordionItem>
      ))}
    </Accordion>
  );
}
