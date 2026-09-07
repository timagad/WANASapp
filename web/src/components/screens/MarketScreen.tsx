"use client";

import { useEffect, useState } from "react";

import { useWanas } from "@/components/Providers";
import { CraftArt } from "@/components/art/CraftArt";
import { ApiError, api, type Product } from "@/lib/api";

export function MarketScreen() {
  const { locale, t, user } = useWanas();
  const [products, setProducts] = useState<Product[] | null>(null);
  const [open, setOpen] = useState<Product | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = () =>
    api
      .products()
      .then(setProducts)
      .catch(() => setProducts([]));

  useEffect(() => {
    void load();
  }, []);

  const order = async (product: Product) => {
    if (!user) {
      setNotice(t.market.signInToOrder);
      return;
    }
    try {
      await api.order(product.id, 1);
      setNotice(t.market.ordered);
      setOpen(null);
      void load();
    } catch (err) {
      setNotice(err instanceof ApiError ? err.message : t.common.error);
    }
  };

  return (
    <section className="screen">
      <div className="eyebrow">{t.market.eyebrow}</div>
      <h1 className="page-title">{t.market.title}</h1>
      <p className="sub">{t.market.subtitle}</p>

      {notice && (
        <p className="mb-3 rounded-xl bg-primary/10 px-3 py-2 text-[12.5px] font-semibold text-primary">
          {notice}
        </p>
      )}

      {products === null ? (
        <div className="grid grid-cols-2 gap-3">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="h-[190px] animate-pulse rounded-2xl bg-line/60" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-3">
          {products.map((product) => (
            <button
              key={product.id}
              type="button"
              onClick={() => setOpen(product)}
              className="overflow-hidden rounded-2xl border border-line bg-white text-start transition hover:-translate-y-0.5"
            >
              <CraftArt category={product.category} className="h-[92px] w-full" />
              <div className="px-3 pb-3 pt-2.5">
                <div className="text-[13px] font-bold leading-tight">
                  {(locale === "ar" || locale === "dz") && product.name_ar
                    ? product.name_ar
                    : product.name}
                </div>
                <div className="mt-0.5 text-[11px] text-muted">
                  {product.artisan_name} · {product.artisan_region}
                </div>
                <div className="mt-1.5 font-display text-[13.5px] font-semibold text-primary-dark">
                  {product.price.display}
                </div>
                <div className="mt-1 text-[10.5px] font-bold text-secondary">
                  ✦ {t.market.story}
                </div>
              </div>
            </button>
          ))}
        </div>
      )}

      {open && (
        <div
          className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 p-0 md:items-center md:p-6"
          onClick={() => setOpen(null)}
          role="presentation"
        >
          <div
            className="max-h-[85vh] w-full max-w-[360px] overflow-y-auto rounded-t-3xl bg-cream p-5 md:rounded-3xl"
            onClick={(event) => event.stopPropagation()}
          >
            <CraftArt
              category={open.category}
              className="mb-3 h-[120px] w-full overflow-hidden rounded-2xl"
            />
            <h2 className="m-0 font-display text-[19px] font-semibold text-primary-dark">
              {(locale === "ar" || locale === "dz") && open.name_ar ? open.name_ar : open.name}
            </h2>
            <p className="mt-0.5 text-[12px] text-muted">
              {t.market.artisan}: {open.artisan_name} · {open.artisan_workshop}
            </p>

            <p className="mt-3 whitespace-pre-wrap text-[13px] leading-relaxed text-ink">
              {open.story}
            </p>

            <dl className="mt-3 space-y-1 text-[12px]">
              <div className="flex gap-2">
                <dt className="font-bold text-primary">{t.market.technique}</dt>
                <dd className="m-0 text-muted">{open.technique}</dd>
              </div>
              <div className="flex gap-2">
                <dt className="font-bold text-primary">{t.market.origin}</dt>
                <dd className="m-0 text-muted">{open.origin}</dd>
              </div>
            </dl>

            <div className="mt-4 flex items-center justify-between gap-3">
              <div>
                <div className="font-display text-[18px] font-semibold text-primary-dark">
                  {open.price.display}
                </div>
                <div className="text-[11px] text-muted">
                  {open.stock > 0 ? `${open.stock} ${t.market.inStock}` : t.market.outOfStock}
                </div>
              </div>
              <button
                type="button"
                disabled={open.stock <= 0}
                onClick={() => void order(open)}
                className="btn-primary"
              >
                {open.stock > 0 ? t.market.buy : t.market.outOfStock}
              </button>
            </div>

            <button type="button" onClick={() => setOpen(null)} className="btn-ghost mt-3 w-full">
              {t.common.cancel}
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
