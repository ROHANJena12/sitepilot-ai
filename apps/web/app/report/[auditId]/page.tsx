import { ReportDashboard } from "@/features/report";

type ReportPageProps = {
  params: Promise<{ auditId: string }>;
};

export default async function Page({ params }: ReportPageProps) {
  const { auditId } = await params;
  return <ReportDashboard auditId={auditId} />;
}
