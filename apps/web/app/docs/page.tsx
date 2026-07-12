import { redirect } from "next/navigation";

import { ROUTES } from "@/shared/constants/routes";

/**
 * Route: /docs
 * Documentation entry redirects to the Help Center.
 */
export default function Page() {
  redirect(ROUTES.help);
}
