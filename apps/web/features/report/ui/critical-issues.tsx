"use client";

import * as React from "react";
import type { ReactNode } from "react";
import { Reveal } from "@/shared/ui/motion";
import { IssueCard } from "@/shared/ui/cards";
import { Heading, Text } from "@/shared/ui/typography";
import type { ReportDashboardView } from "../model/map-api-report";

type Issue = ReportDashboardView["issues"][number];

type CriticalIssuesProps = {
  issues: Issue[];
  renderAi?: (issue: Issue) => ReactNode;
};

function subscribeLg(onStoreChange: () => void) {
  const media = window.matchMedia("(min-width: 1024px)");
  media.addEventListener("change", onStoreChange);
  return () => media.removeEventListener("change", onStoreChange);
}

function getLgSnapshot() {
  return window.matchMedia("(min-width: 1024px)").matches;
}

function getLgServerSnapshot() {
  return false;
}

/** Desktop two-column breakpoint — only one layout tree mounts at a time. */
function useIsDesktopColumns() {
  return React.useSyncExternalStore(subscribeLg, getLgSnapshot, getLgServerSnapshot);
}

function FindingItem({
  issue,
  index,
  renderAi,
}: {
  issue: Issue;
  index: number;
  renderAi?: (issue: Issue) => ReactNode;
}) {
  return (
    <li className="min-w-0">
      <Reveal delay={0.03 * Math.min(index, 5)}>
        <IssueCard
          title={issue.title}
          severity={issue.severity}
          category={issue.category}
          description={issue.description}
          businessImpact={issue.businessImpact}
          effort={issue.effort}
          confidence={issue.confidence}
          status={issue.status}
        >
          {renderAi?.(issue)}
        </IssueCard>
      </Reveal>
    </li>
  );
}

/**
 * Two independent vertical stacks on desktop; one column on mobile.
 * Expanding a card only lengthens its own stack — cards never change columns.
 */
export function CriticalIssues({ issues, renderAi }: CriticalIssuesProps) {
  const isDesktop = useIsDesktopColumns();

  if (!issues.length) {
    return (
      <section aria-labelledby="issues-heading" className="space-y-3">
        <Heading id="issues-heading" level="h2" className="text-lg md:text-xl">
          Critical issues
        </Heading>
        <Text variant="muted">No critical or high-severity findings in this report.</Text>
      </section>
    );
  }

  const left = issues.filter((_, index) => index % 2 === 0);
  const right = issues.filter((_, index) => index % 2 === 1);

  return (
    <section aria-labelledby="issues-heading" className="space-y-6">
      <Reveal>
        <div>
          <Heading id="issues-heading" level="h2" className="text-lg md:text-xl">
            Critical issues
          </Heading>
          <Text variant="muted" className="mt-1 max-w-2xl">
            Prioritized findings with severity, confidence, and business context.
          </Text>
        </div>
      </Reveal>

      {isDesktop ? (
        <div className="grid grid-cols-2 items-start gap-5">
          <ul className="m-0 flex list-none flex-col gap-4 p-0">
            {left.map((issue, index) => (
              <FindingItem
                key={issue.id}
                issue={issue}
                index={index * 2}
                renderAi={renderAi}
              />
            ))}
          </ul>
          <ul className="m-0 flex list-none flex-col gap-4 p-0">
            {right.map((issue, index) => (
              <FindingItem
                key={issue.id}
                issue={issue}
                index={index * 2 + 1}
                renderAi={renderAi}
              />
            ))}
          </ul>
        </div>
      ) : (
        <ul className="m-0 flex list-none flex-col gap-4 p-0">
          {issues.map((issue, index) => (
            <FindingItem
              key={issue.id}
              issue={issue}
              index={index}
              renderAi={renderAi}
            />
          ))}
        </ul>
      )}
    </section>
  );
}
