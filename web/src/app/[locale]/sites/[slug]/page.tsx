import { SiteScreen } from "@/components/screens/SiteScreen";

export default async function Page({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  return <SiteScreen slug={slug} />;
}
