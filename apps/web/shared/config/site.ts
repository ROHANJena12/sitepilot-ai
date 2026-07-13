import { ROUTES } from "@/shared/constants/routes";

export const siteConfig = {
  name: "SitePilot AI",
  tagline: "Your AI-powered Website Intelligence Platform.",
  description:
    "Analyze any public website and get a business-ready health report — SEO, performance, security, accessibility, and AI recommendations that explain what to fix first.",
  url: "https://sitepilot.ai",
  email: "jenarohan23@gmail.com",
  links: {
    github: "https://github.com/sitepilot-ai",
    linkedin: "https://www.linkedin.com/company/sitepilot-ai",
  },
} as const;

export const marketingNav = [
  { label: "About", href: ROUTES.about },
  { label: "Help", href: ROUTES.help },
  { label: "Contact", href: ROUTES.contact },
] as const;

export const footerNav = {
  product: [
    { label: "Features", href: "/#features" },
    { label: "How it works", href: "/#how-it-works" },
    { label: "Help Center", href: ROUTES.help },
    { label: "FAQ", href: ROUTES.faq },
  ],
  company: [
    { label: "About", href: ROUTES.about },
    { label: "Contact", href: ROUTES.contact },
  ],
  legal: [
    { label: "Privacy Policy", href: ROUTES.privacy },
    { label: "Terms & Conditions", href: ROUTES.terms },
  ],
} as const;
