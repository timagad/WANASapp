import type { Metadata, Viewport } from "next";
import { notFound } from "next/navigation";

import "@/app/globals.css";
import { Providers } from "@/components/Providers";
import { Shell } from "@/components/Shell";
import { LOCALES, direction, getMessages, isLocale } from "@/lib/i18n";

export const metadata: Metadata = {
  title: "WANAS — Votre compagnon de voyage en Algérie",
  description:
    "Guide conversationnel ancré dans un corpus patrimonial vérifié, itinéraires personnalisés, réservations, artisanat et réalité augmentée.",
  manifest: "/manifest.webmanifest",
  applicationName: "WANAS",
};

export const viewport: Viewport = {
  themeColor: "#12463A",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export function generateStaticParams() {
  return LOCALES.map((locale) => ({ locale }));
}

export default async function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();

  const messages = getMessages(locale);
  const dir = direction(locale);

  return (
    <html lang={locale} dir={dir}>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,700&family=Manrope:wght@400;500;600;700;800&family=Noto+Kufi+Arabic:wght@400;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <Providers locale={locale} messages={messages} dir={dir}>
          <Shell>{children}</Shell>
        </Providers>
      </body>
    </html>
  );
}
