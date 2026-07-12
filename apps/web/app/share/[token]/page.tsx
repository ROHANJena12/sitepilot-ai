import { ReportDashboard } from "@/features/report";

type SharePageProps = {
  params: Promise<{ token: string }>;
};

export default async function Page({ params }: SharePageProps) {
  const { token } = await params;
  return <ReportDashboard shareToken={token} readonly />;
}
