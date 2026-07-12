"use client";

import Link from "next/link";

import { ROUTES } from "@/shared/constants/routes";
import { Reveal } from "@/shared/ui/motion";
import { Button } from "@/shared/ui/buttons";
import { Card, CardContent, CardHeader } from "@/shared/ui/cards";
import { Heading, Text } from "@/shared/ui/typography";

type ActionPanelProps = {
  auditId: string;
  readonly?: boolean;
};

/**
 * Bottom guidance only — Export / Share live in the report header to avoid duplicates.
 */
export function ActionPanel({ readonly = false }: ActionPanelProps) {
  if (readonly) return null;

  return (
    <Reveal>
      <section aria-labelledby="actions-heading">
        <Card>
          <CardHeader className="space-y-2">
            <Heading id="actions-heading" level="h2" className="text-lg md:text-xl">
              Next steps
            </Heading>
            <Text variant="muted">
              Use Export or Share in the header to download this report or create a
              read-only link. Shared viewers cannot regenerate AI, export, or change
              the audit.
            </Text>
          </CardHeader>
          <CardContent>
            <Button asChild variant="secondary" size="sm">
              <Link href={ROUTES.audit}>Run another audit</Link>
            </Button>
          </CardContent>
        </Card>
      </section>
    </Reveal>
  );
}
