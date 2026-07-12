import { MarketingNavbar } from "@/widgets/navbar";
import { MarketingFooter } from "@/widgets/footer";

type MarketingShellProps = {
  children: React.ReactNode;
  /** Optional main landmark labelledby id for the page H1. */
  labelledBy?: string;
};

/**
 * Shared chrome for public marketing / legal pages.
 * Keeps report/audit flows free of marketing clutter by isolating layout here.
 */
export function MarketingShell({ children, labelledBy }: MarketingShellProps) {
  return (
    <>
      <a href="#main-content" className="skip-link">
        Skip to content
      </a>
      <MarketingNavbar />
      <main id="main-content" aria-labelledby={labelledBy}>
        {children}
      </main>
      <MarketingFooter />
    </>
  );
}
