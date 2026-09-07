"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { Icon } from "@/components/Icon";
import { useWanas } from "@/components/Providers";
import { SiteArt } from "@/components/art/SiteArt";
import { api, type Site } from "@/lib/api";

/** Arabic and Darija readers get the Arabic name when the catalogue has one. */
export function siteName(site: Site, locale: string): string {
  return (locale === "ar" || locale === "dz") && site.name_ar ? site.name_ar : site.name;
}

export function SiteCard({ site, reason }: { site: Site; reason?: string }) {
  const { locale, t } = useWanas();
  const router = useRouter();

  const openAr = (event: React.MouseEvent) => {
    event.preventDefault();
    event.stopPropagation();
    void api.recordEvent(site.slug, "ar_open").catch(() => undefined);
    router.push(`/${locale}/ar?site=${site.slug}`);
  };

  return (
    <Link href={`/${locale}/sites/${site.slug}`} className="site-card">
      <div className="relative h-[92px]">
        <SiteArt slug={site.slug} category={site.category} className="h-full w-full" />
        {site.has_ar && (
          <button type="button" onClick={openAr} className="ar-badge" aria-label={t.site.ar}>
            <Icon name="camera" className="h-2.5 w-2.5" strokeWidth={2.5} />
            AR
          </button>
        )}
      </div>
      <div className="px-3 pb-3 pt-2.5">
        <div className="text-[13px] font-bold leading-tight">{siteName(site, locale)}</div>
        <div className="mt-1 text-[10.5px] font-bold uppercase tracking-wide text-secondary">
          {site.unesco ? t.site.unesco : site.region}
        </div>
        {reason === "similar-visitors" && (
          <div className="mt-1 text-[10px] text-muted">↗ {site.category}</div>
        )}
      </div>
    </Link>
  );
}
