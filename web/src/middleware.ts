import { NextRequest, NextResponse } from "next/server";

import { DEFAULT_LOCALE, LOCALES } from "@/lib/i18n";

const PUBLIC_FILE = /\.(.*)$/;

/**
 * Every page lives under /<locale>. A request without one is redirected to the
 * best match from Accept-Language, falling back to French — the working language
 * of the dossier and the most common second language of the target audience.
 */
export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (
    pathname.startsWith("/_next") ||
    pathname.startsWith("/api") ||
    PUBLIC_FILE.test(pathname)
  ) {
    return NextResponse.next();
  }

  const hasLocale = LOCALES.some(
    (locale) => pathname === `/${locale}` || pathname.startsWith(`/${locale}/`),
  );
  if (hasLocale) return NextResponse.next();

  const preferred = request.headers.get("accept-language") ?? "";
  const matched =
    LOCALES.find((locale) => preferred.toLowerCase().startsWith(locale)) ??
    (preferred.toLowerCase().startsWith("ar") ? "ar" : DEFAULT_LOCALE);

  const url = request.nextUrl.clone();
  url.pathname = `/${matched}${pathname === "/" ? "" : pathname}`;
  return NextResponse.redirect(url);
}

export const config = {
  matcher: ["/((?!_next|.*\..*).*)"],
};
