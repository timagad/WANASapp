"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Icon } from "@/components/Icon";
import { useWanas } from "@/components/Providers";
import { siteName } from "@/components/SiteCard";
import { SiteArt } from "@/components/art/SiteArt";
import { ApiError, api, type ServiceOffer, type Site } from "@/lib/api";

export function SiteScreen({ slug }: { slug: string }) {
  const { locale, t } = useWanas();
  const [site, setSite] = useState<Site | null>(null);
  const [services, setServices] = useState<ServiceOffer[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .site(slug)
      .then((value) => {
        setSite(value);
        return api.services({ region: value.region });
      })
      .then((offers) => setServices(offers ?? []))
      .catch((err) =>
        setError(err instanceof ApiError && err.status === 0 ? t.common.apiDown : t.common.error),
      );
  }, [slug, t.common.apiDown, t.common.error]);

  if (error) {
    return (
      <section className="screen">
        <p className="text-[13px] text-secondary">{error}</p>
      </section>
    );
  }

  if (!site) {
    return (
      <section className="screen">
        <div className="h-[150px] animate-pulse rounded-2xl bg-line/60" />
      </section>
    );
  }

  const summary = (locale === "ar" || locale === "dz") && site.summary_ar ? site.summary_ar : site.summary;

  return (
    <section className="screen">
      <div className="mb-3 flex items-center justify-between">
        <Link
          href={`/${locale}`}
          className="flex h-8 w-8 items-center justify-center rounded-full border border-line bg-white text-primary"
          aria-label={t.common.back}
        >
          <Icon name="chevronLeft" className="h-4 w-4 rtl:rotate-180" strokeWidth={2.2} />
        </Link>
        {site.unesco && (
          <span className="rounded-full bg-accent/25 px-2.5 py-1 text-[10px] font-extrabold uppercase tracking-wide text-primary-dark">
            {t.site.unesco}
          </span>
        )}
      </div>

      <SiteArt
        slug={site.slug}
        category={site.category}
        className="mb-4 h-[150px] w-full overflow-hidden rounded-2xl"
      />

      <div className="eyebrow">{site.region}</div>
      <h1 className="page-title">{siteName(site, locale)}</h1>
      <p className="sub">{summary}</p>

      <dl className="mb-4 grid grid-cols-2 gap-2 text-[12px]">
        <Fact label={t.site.visit} value={`${site.typical_visit_minutes} ${t.common.minutes}`} />
        <Fact label={t.site.hours} value={site.best_hours} />
        <Fact
          label={t.site.fee}
          value={site.entry_fee.centimes === 0 ? t.site.free : site.entry_fee.display}
        />
        <Fact label="Accès" value={t.site.accessibility[site.accessibility]} />
      </dl>

      <div className="flex flex-wrap gap-2">
        <Link
          href={`/${locale}/guide?q=${encodeURIComponent(`${t.site.tellMeMore}: ${site.name}`)}`}
          className="btn-primary"
        >
          <Icon name="sparkle" className="h-4 w-4" />
          {t.site.tellMeMore}
        </Link>
        {site.has_ar && (
          <Link href={`/${locale}/ar?site=${site.slug}`} className="btn-ghost">
            <Icon name="camera" className="h-4 w-4" />
            {t.site.ar}
          </Link>
        )}
      </div>

      {services.length > 0 && (
        <>
          <div className="section-title">{t.site.book}</div>
          <ul className="m-0 list-none space-y-2 p-0">
            {services.map((service) => (
              <li key={service.id} className="card !p-3">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="text-[13px] font-bold text-ink">{service.title}</div>
                    <div className="text-[11.5px] text-muted">
                      {service.provider_name}
                      {service.certified && <span className="text-primary"> · ✓</span>} ·{" "}
                      {service.languages.join(" / ")}
                    </div>
                  </div>
                  <div className="shrink-0 text-end">
                    <div className="font-display text-[13.5px] font-semibold text-primary-dark">
                      {service.price.display}
                    </div>
                    <div className="text-[11px] text-muted">
                      {service.duration_minutes} {t.common.minutes}
                    </div>
                  </div>
                </div>
                <p className="mt-1.5 text-[12px] leading-snug text-muted">{service.description}</p>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-line bg-white px-3 py-2">
      <dt className="text-[10px] font-bold uppercase tracking-wide text-muted">{label}</dt>
      <dd className="m-0 mt-0.5 text-[12.5px] font-semibold text-ink">{value}</dd>
    </div>
  );
}
