"use client";

import * as React from "react";

import { siteConfig } from "@/shared/config/site";
import { Button } from "@/shared/ui/buttons";
import { Input, Label, Textarea } from "@/shared/ui/forms";
import { Text } from "@/shared/ui/typography";

/**
 * Frontend-only contact form. No API — validates locally, then shows coming-soon.
 */
export function ContactForm() {
  const [submitted, setSubmitted] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitted) return;

    const form = event.currentTarget;
    const data = new FormData(form);
    const name = String(data.get("name") ?? "").trim();
    const email = String(data.get("email") ?? "").trim();
    const subject = String(data.get("subject") ?? "").trim();
    const message = String(data.get("message") ?? "").trim();

    if (!name || !email || !subject || !message) {
      setError("Please fill in name, email, subject, and message.");
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setError("Enter a valid email address.");
      return;
    }

    setError(null);
    setSubmitted(true);
  }

  return (
    <form
      onSubmit={onSubmit}
      className="space-y-5 rounded-xl border border-border bg-surface p-6 md:p-8"
      aria-describedby={submitted ? "contact-coming-soon" : error ? "contact-form-error" : undefined}
    >
      <div className="grid gap-5 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="contact-name">Name</Label>
          <Input
            id="contact-name"
            name="name"
            autoComplete="name"
            placeholder="Alex Rivera"
            required
            disabled={submitted}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="contact-email">Email</Label>
          <Input
            id="contact-email"
            name="email"
            type="email"
            autoComplete="email"
            placeholder="alex@company.com"
            required
            disabled={submitted}
          />
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="contact-subject">Subject</Label>
        <Input
          id="contact-subject"
          name="subject"
          placeholder="Question about SitePilot"
          required
          disabled={submitted}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="contact-message">Message</Label>
        <Textarea
          id="contact-message"
          name="message"
          rows={6}
          placeholder="How can we help?"
          required
          disabled={submitted}
        />
      </div>

      {error ? (
        <Text id="contact-form-error" role="alert" className="text-sm text-danger">
          {error}
        </Text>
      ) : null}

      {submitted ? (
        <Text
          id="contact-coming-soon"
          role="status"
          className="rounded-md border border-border bg-bg-subtle px-3 py-2 text-sm text-foreground"
        >
          Contact functionality coming soon. Please email{" "}
          <a
            href={`mailto:${siteConfig.email}`}
            className="font-medium text-accent underline-offset-4 hover:underline"
          >
            {siteConfig.email}
          </a>{" "}
          for now.
        </Text>
      ) : null}

      <Button type="submit" size="lg" className="w-full sm:w-auto" disabled={submitted}>
        {submitted ? "Submitted" : "Send message"}
      </Button>
    </form>
  );
}
