import ar from "@/messages/ar.json";
import dz from "@/messages/dz.json";
import en from "@/messages/en.json";
import fr from "@/messages/fr.json";
import kab from "@/messages/kab.json";

export const LOCALES = ["fr", "ar", "dz", "kab", "en"] as const;
export type Locale = (typeof LOCALES)[number];

// The `fr` bundle is the reference shape; every other bundle is type-checked
// against it, so a missing key is a build error rather than a blank label.
export type Messages = typeof fr;

const BUNDLES: Record<Locale, Messages> = { fr, ar: ar as Messages, dz: dz as Messages, kab: kab as Messages, en };

export const DEFAULT_LOCALE: Locale = "fr";

/** Arabic and Darija are written right to left; Tamazight here uses Latin script. */
export const RTL_LOCALES: Locale[] = ["ar", "dz"];

export function isLocale(value: string): value is Locale {
  return (LOCALES as readonly string[]).includes(value);
}

export function getMessages(locale: Locale): Messages {
  return BUNDLES[locale] ?? BUNDLES[DEFAULT_LOCALE];
}

export function direction(locale: Locale): "rtl" | "ltr" {
  return RTL_LOCALES.includes(locale) ? "rtl" : "ltr";
}

export const LOCALE_LABELS: Record<Locale, string> = {
  fr: "Français",
  ar: "العربية",
  dz: "الدارجة",
  kab: "Tamaziɣt",
  en: "English",
};

/** Algerian convention: DD/MM/YYYY. */
export function formatDate(value: string | Date, locale: Locale): string {
  const date = typeof value === "string" ? new Date(value) : value;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(date.getDate())}/${pad(date.getMonth() + 1)}/${date.getFullYear()}`;
}
