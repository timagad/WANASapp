"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Icon } from "@/components/Icon";
import { useWanas } from "@/components/Providers";
import { ApiError, api, type Booking, type Order } from "@/lib/api";
import { LOCALES, LOCALE_LABELS, formatDate, type Locale } from "@/lib/i18n";

const INTERESTS = [
  "history",
  "nature",
  "spirituality",
  "gastronomy",
  "crafts",
  "relaxation",
  "culture",
  "family",
] as const;

export function ProfileScreen() {
  const { locale, t, user, refreshUser, signOut } = useWanas();
  const router = useRouter();
  const pathname = usePathname();

  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);

  useEffect(() => {
    if (!user) {
      setBookings([]);
      setOrders([]);
      return;
    }
    api.bookings().then(setBookings).catch(() => setBookings([]));
    api.orders().then(setOrders).catch(() => setOrders([]));
  }, [user]);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (mode === "login") {
        await api.login(email, password);
      } else {
        await api.register({ email, password, name, preferred_language: locale });
      }
      await refreshUser();
      setPassword("");
    } catch (err) {
      setError(err instanceof ApiError && err.status === 0 ? t.common.apiDown : t.profile.authError);
    } finally {
      setBusy(false);
    }
  };

  const toggleInterest = async (interest: string) => {
    if (!user) return;
    const next = { ...user.interests };
    if (next[interest]) delete next[interest];
    else next[interest] = 1;
    await api.setInterests(next).catch(() => undefined);
    await refreshUser();
  };

  const switchLocale = (next: Locale) => {
    const rest = pathname.replace(`/${locale}`, "") || "";
    router.push(`/${next}${rest}`);
  };

  return (
    <section className="screen">
      <div className="eyebrow">{t.profile.eyebrow}</div>
      <h1 className="page-title">{t.profile.title}</h1>
      <p className="sub">{t.profile.subtitle}</p>

      {user ? (
        <div className="mb-5 flex items-center gap-3">
          <div className="flex h-[46px] w-[46px] items-center justify-center rounded-full bg-gradient-to-br from-secondary to-accent text-[17px] font-bold text-white">
            {user.name.charAt(0).toUpperCase()}
          </div>
          <div>
            <div className="font-display text-[16px] font-semibold text-primary-dark">
              {user.name}
            </div>
            <div className="text-[12px] text-muted">
              {t.profile.member} · {user.email}
            </div>
          </div>
          <button type="button" onClick={signOut} className="btn-ghost ms-auto !px-3 !py-1.5">
            {t.profile.signOut}
          </button>
        </div>
      ) : (
        <form onSubmit={submit} className="card mb-5 space-y-2">
          <div className="flex gap-2">
            {(["login", "register"] as const).map((option) => (
              <button
                key={option}
                type="button"
                onClick={() => setMode(option)}
                className={`lang-chip ${mode === option ? "lang-chip-active" : ""}`}
              >
                {option === "login" ? t.profile.signIn : t.profile.signUp}
              </button>
            ))}
          </div>
          {mode === "register" && (
            <input
              className="field"
              placeholder={t.profile.name}
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          )}
          <input
            className="field"
            type="email"
            autoComplete="email"
            placeholder={t.profile.email}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <input
            className="field"
            type="password"
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            placeholder={t.profile.password}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            minLength={8}
            required
          />
          <button type="submit" disabled={busy} className="btn-primary w-full">
            {mode === "login" ? t.profile.signIn : t.profile.signUp}
          </button>
          {error && <p className="m-0 text-[12px] text-secondary">{error}</p>}
          <p className="m-0 text-[11px] leading-snug text-muted">{t.profile.demoHint}</p>
        </form>
      )}

      <div className="section-title !mt-0">{t.profile.language}</div>
      <div className="mb-5 flex flex-wrap gap-2">
        {LOCALES.map((option) => (
          <button
            key={option}
            type="button"
            onClick={() => switchLocale(option)}
            className={`lang-chip ${option === locale ? "lang-chip-active" : ""}`}
            lang={option}
          >
            {LOCALE_LABELS[option]}
          </button>
        ))}
      </div>

      {user && (
        <>
          <div className="section-title !mt-0">{t.profile.interests}</div>
          <div className="mb-5 flex flex-wrap gap-2">
            {INTERESTS.map((interest) => (
              <button
                key={interest}
                type="button"
                onClick={() => void toggleInterest(interest)}
                className={`chip ${user.interests[interest] ? "chip-active" : ""}`}
              >
                {interest}
              </button>
            ))}
          </div>

          <div className="section-title">{t.profile.bookings}</div>
          {bookings.length === 0 ? (
            <p className="text-[12.5px] text-muted">{t.profile.noBookings}</p>
          ) : (
            <ul className="m-0 list-none space-y-2 p-0">
              {bookings.map((booking) => (
                <li key={booking.id} className="card !p-3">
                  <div className="flex items-center justify-between text-[13px] font-bold">
                    {booking.service_title}
                    <span className="text-[11px] uppercase text-secondary">{booking.status}</span>
                  </div>
                  <div className="text-[11.5px] text-muted">
                    {formatDate(booking.scheduled_for, locale)} · {booking.party_size} ·{" "}
                    {booking.amount.display}
                  </div>
                </li>
              ))}
            </ul>
          )}

          <div className="section-title">{t.profile.orders}</div>
          {orders.length === 0 ? (
            <p className="text-[12.5px] text-muted">{t.profile.noOrders}</p>
          ) : (
            <ul className="m-0 list-none space-y-2 p-0">
              {orders.map((order) => (
                <li key={order.id} className="card !p-3">
                  <div className="text-[13px] font-bold">{order.product_name}</div>
                  <div className="text-[11.5px] text-muted">
                    ×{order.quantity} · {order.total.display} · {formatDate(order.created_at, locale)}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </>
      )}

      <div className="mt-5 flex items-center justify-between rounded-[18px] bg-primary p-4 text-white">
        <div>
          <div className="font-display text-[14.5px] font-semibold">{t.profile.partner}</div>
          <div className="text-[12px] text-[#BFE0D3]">{t.profile.partnerCta}</div>
        </div>
        <Icon name="chevron" className="h-4 w-4 rtl:rotate-180" strokeWidth={2.2} />
      </div>

      <div className="section-title">{t.profile.proAccess}</div>
      <Link
        href={`/${locale}/dashboard`}
        className="flex items-center gap-3 rounded-2xl border border-line bg-white p-3"
      >
        <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary text-white">
          <Icon name="chart" className="h-[18px] w-[18px]" />
        </span>
        <span className="flex-1">
          <span className="block text-[13px] font-bold text-ink">{t.profile.dashboard}</span>
          <span className="block text-[11.5px] text-muted">{t.profile.dashboardSub}</span>
        </span>
        <Icon name="chevron" className="h-4 w-4 text-muted rtl:rotate-180" />
      </Link>
    </section>
  );
}
