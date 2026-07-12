"use client";

import * as React from "react";
import Link from "next/link";
import { Menu, Github } from "lucide-react";

import { cn } from "@/shared/lib/utils";
import { marketingNav, siteConfig } from "@/shared/config/site";
import { ROUTES } from "@/shared/constants/routes";
import { BrandLogo } from "@/shared/ui/brand";
import { Button } from "@/shared/ui/buttons";
import {
  Drawer,
  DrawerClose,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
  DrawerTrigger,
} from "@/shared/ui/feedback";
import { Container } from "@/shared/ui/layout";
import { ThemeToggle } from "@/shared/ui/theme-toggle";

export function MarketingNavbar() {
  const [scrolled, setScrolled] = React.useState(false);

  React.useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={cn(
        "sticky top-0 z-40 w-full border-b transition-colors duration-base",
        scrolled
          ? "border-border bg-bg/80 backdrop-blur-md"
          : "border-transparent bg-transparent",
      )}
    >
      <Container className="flex h-14 max-w-[1200px] items-center justify-between gap-4 md:h-16">
        <BrandLogo size="sm" />

        <nav className="hidden items-center gap-1 md:flex" aria-label="Primary">
          {marketingNav.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="rounded-md px-3 py-2 text-sm text-foreground-muted transition-colors duration-fast hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          <a
            href={siteConfig.links.github}
            target="_blank"
            rel="noopener noreferrer"
            className="hidden rounded-md p-2 text-foreground-muted transition-colors duration-fast hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg sm:inline-flex"
            aria-label="SitePilot AI on GitHub"
          >
            <Github className="h-4 w-4" aria-hidden />
          </a>
          <ThemeToggle />
          <Button asChild size="sm" className="hidden sm:inline-flex">
            <Link href={ROUTES.audit}>Analyze Website</Link>
          </Button>

          <Drawer>
            <DrawerTrigger asChild>
              <Button
                variant="secondary"
                size="icon"
                className="md:hidden"
                aria-label="Open menu"
              >
                <Menu className="h-4 w-4" />
              </Button>
            </DrawerTrigger>
            <DrawerContent side="right" className="gap-6">
              <DrawerHeader>
                <DrawerTitle className="sr-only">Navigation</DrawerTitle>
                <BrandLogo size="sm" />
              </DrawerHeader>
              <nav className="flex flex-col gap-1" aria-label="Mobile">
                {marketingNav.map((item) => (
                  <DrawerClose asChild key={item.href}>
                    <Link
                      href={item.href}
                      className="rounded-md px-3 py-3 text-base text-foreground transition-colors hover:bg-surface-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                    >
                      {item.label}
                    </Link>
                  </DrawerClose>
                ))}
                <DrawerClose asChild>
                  <a
                    href={siteConfig.links.github}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="rounded-md px-3 py-3 text-base text-foreground transition-colors hover:bg-surface-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                  >
                    GitHub
                  </a>
                </DrawerClose>
              </nav>
              <DrawerClose asChild>
                <Link
                  href={ROUTES.audit}
                  className="inline-flex h-10 w-full items-center justify-center gap-2 rounded-md bg-accent px-4 text-sm font-medium text-accent-foreground transition-colors hover:bg-accent-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
                >
                  Analyze Website
                </Link>
              </DrawerClose>
            </DrawerContent>
          </Drawer>
        </div>
      </Container>
    </header>
  );
}
