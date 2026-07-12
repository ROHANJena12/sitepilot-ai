import { cn } from "@/shared/lib/utils";

type ProseProps = {
  children: React.ReactNode;
  className?: string;
};

/**
 * Readable long-form content for legal and help pages.
 * Uses existing typography tokens — not a second prose theme.
 */
export function Prose({ children, className }: ProseProps) {
  return (
    <div
      className={cn(
        "max-w-none space-y-4 text-sm leading-relaxed text-foreground-muted md:text-[15px]",
        "[&_h2]:mt-10 [&_h2]:scroll-mt-24 [&_h2]:text-xl [&_h2]:font-semibold [&_h2]:tracking-tight [&_h2]:text-foreground md:[&_h2]:text-2xl",
        "[&_h3]:mt-6 [&_h3]:scroll-mt-24 [&_h3]:text-base [&_h3]:font-semibold [&_h3]:text-foreground md:[&_h3]:text-lg",
        "[&_p]:text-foreground-muted",
        "[&_ul]:list-disc [&_ul]:space-y-2 [&_ul]:pl-5",
        "[&_ol]:list-decimal [&_ol]:space-y-2 [&_ol]:pl-5",
        "[&_li]:text-foreground-muted",
        "[&_a]:font-medium [&_a]:text-accent [&_a]:underline-offset-4 hover:[&_a]:underline",
        "[&_strong]:font-medium [&_strong]:text-foreground",
        className,
      )}
    >
      {children}
    </div>
  );
}
