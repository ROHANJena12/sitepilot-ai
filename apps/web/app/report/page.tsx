import { redirect } from "next/navigation";

import { ROUTES } from "@/shared/constants/routes";

/**
 * Route: /report
 * Redirect to audit entry — live reports live at /report/[auditId].
 */
export default function Page() {
  redirect(ROUTES.audit);
}
