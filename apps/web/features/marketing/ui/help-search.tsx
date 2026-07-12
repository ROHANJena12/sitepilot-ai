"use client";

import * as React from "react";
import Link from "next/link";
import { Search } from "lucide-react";

import { ROUTES } from "@/shared/constants/routes";
import { Input } from "@/shared/ui/forms";
import { Heading, Text } from "@/shared/ui/typography";

export type HelpSection = {
  id: string;
  title: string;
  summary: string;
  items: readonly string[];
  links?: readonly { label: string; href: string }[];
};

type HelpSearchProps = {
  sections: readonly HelpSection[];
};

export function HelpSearch({ sections }: HelpSearchProps) {
  const [query, setQuery] = React.useState("");
  const normalized = query.trim().toLowerCase();

  const visible = React.useMemo(() => {
    if (!normalized) return sections;
    return sections.filter((section) => {
      const haystack = [
        section.title,
        section.summary,
        ...section.items,
        ...(section.links?.map((l) => l.label) ?? []),
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(normalized);
    });
  }, [normalized, sections]);

  return (
    <div className="space-y-10">
      <div className="relative mx-auto max-w-xl">
        <label htmlFor="help-search" className="sr-only">
          Search help topics
        </label>
        <Search
          className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-foreground-subtle"
          aria-hidden
        />
        <Input
          id="help-search"
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search getting started, scores, sharing…"
          className="pl-9"
          autoComplete="off"
        />
      </div>

      {visible.length === 0 ? (
        <Text variant="muted" className="text-center" role="status">
          No topics matched “{query}”. Try “audit”, “share”, or “export”.
        </Text>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {visible.map((section) => (
            <article
              key={section.id}
              id={section.id}
              className="scroll-mt-24 rounded-xl border border-border bg-surface p-5 md:p-6"
              aria-labelledby={`${section.id}-title`}
            >
              <Heading id={`${section.id}-title`} level="h3" as="h2">
                {section.title}
              </Heading>
              <Text variant="muted" className="mt-2">
                {section.summary}
              </Text>
              <ul className="mt-4 space-y-2">
                {section.items.map((item) => (
                  <li key={item} className="flex gap-2 text-sm text-foreground-muted">
                    <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-accent" aria-hidden />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
              {section.links && section.links.length > 0 ? (
                <ul className="mt-5 flex flex-wrap gap-x-4 gap-y-2 border-t border-border pt-4">
                  {section.links.map((link) => (
                    <li key={link.href}>
                      <Link
                        href={link.href}
                        className="text-sm font-medium text-accent underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                      >
                        {link.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              ) : null}
            </article>
          ))}
        </div>
      )}

      <Text variant="caption" className="text-center text-foreground-subtle">
        Still stuck? Visit{" "}
        <Link href={ROUTES.faq} className="text-accent underline-offset-4 hover:underline">
          FAQ
        </Link>{" "}
        or{" "}
        <Link href={ROUTES.contact} className="text-accent underline-offset-4 hover:underline">
          Contact
        </Link>
        .
      </Text>
    </div>
  );
}
