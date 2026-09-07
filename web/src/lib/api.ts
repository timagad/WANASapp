/**
 * Typed client for the WANAS API.
 *
 * Tokens live in localStorage, which is deliberate for a Phase 1 PWA served
 * from a different origin than the API: there is no cookie to share. Phase 2
 * moves to same-origin httpOnly cookies once the API sits behind the same
 * gateway as the web app.
 */

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://localhost:8000";

const ACCESS_KEY = "wanas.access";
const REFRESH_KEY = "wanas.refresh";

export type Money = { centimes: number; display: string };

export type Site = {
  id: string;
  slug: string;
  name: string;
  name_ar: string;
  region: string;
  category: string;
  tags: string[];
  latitude: number;
  longitude: number;
  summary: string;
  summary_ar: string;
  unesco: boolean;
  has_ar: boolean;
  ar_marker: string | null;
  typical_visit_minutes: number;
  best_hours: string;
  accessibility: "easy" | "moderate" | "hard";
  entry_fee: Money;
};

export type Recommendation = { site: Site; score: number; reason: string };

export type Source = {
  ref: number;
  id: string;
  title: string;
  source: string;
  site_slug: string | null;
  score: number;
};

export type Answer = {
  answer: string;
  sources: Source[];
  conversation_id: string | null;
  provider: string;
  grounded: boolean;
  refused: boolean;
  cached: boolean;
  rtl: boolean;
};

export type Stop = {
  site_id: string | null;
  label: string;
  arrive_at: string;
  dwell_minutes: number;
  tip: string;
  site: Site | null;
};

export type Day = { index: number; travel_km: number; stops: Stop[] };

export type Itinerary = {
  id: string | null;
  title: string;
  days: number;
  party_size: number;
  budget_band: string;
  mobility: string;
  interests: string[];
  language: string;
  start_date: string | null;
  plan: Day[];
};

export type Product = {
  id: string;
  name: string;
  name_ar: string;
  category: string;
  price: Money;
  stock: number;
  technique: string;
  origin: string;
  story: string;
  story_is_ai_drafted: boolean;
  artisan_name: string;
  artisan_region: string;
  artisan_workshop: string;
};

export type ServiceOffer = {
  id: string;
  title: string;
  description: string;
  price: Money;
  duration_minutes: number;
  max_party: number;
  provider_name: string;
  provider_type: string;
  region: string;
  languages: string[];
  certified: boolean;
  rating: number;
};

export type Booking = {
  id: string;
  service_id: string;
  service_title: string;
  status: string;
  scheduled_for: string;
  party_size: number;
  amount: Money;
  created_at: string;
};

export type Order = {
  id: string;
  product_id: string;
  product_name: string;
  quantity: number;
  unit_price: Money;
  total: Money;
  status: string;
  created_at: string;
};

export type User = {
  id: string;
  email: string;
  name: string;
  preferred_language: string;
  user_type: string;
  interests: Record<string, number>;
  home_region: string | null;
};

export type Dashboard = {
  generated_at: string;
  cohort_floor: number;
  active_visitors: number | null;
  average_stay_days: number | null;
  by_region: { region: string; visitors: number; share_of_peak: number }[];
  trends: { region: string; change_pct: number; direction: "up" | "down" }[];
  suppressed: string[];
  note: string;
};

export type VisionResult = {
  site: Site | null;
  confidence: number;
  method: string;
  narrative: string;
  sources: Source[];
  nearby: Site[];
};

export type Health = {
  status: string;
  llm: string;
  cache: string;
  languages: string[];
};

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

export const tokens = {
  access: () => (typeof window === "undefined" ? null : localStorage.getItem(ACCESS_KEY)),
  refresh: () => (typeof window === "undefined" ? null : localStorage.getItem(REFRESH_KEY)),
  set(access: string, refresh: string) {
    localStorage.setItem(ACCESS_KEY, access);
    localStorage.setItem(REFRESH_KEY, refresh);
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

async function parseError(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body?.detail === "string") return body.detail;
    if (Array.isArray(body?.detail)) return body.detail.map((d: { msg: string }) => d.msg).join(", ");
  } catch {
    /* fall through to the status text */
  }
  return response.statusText || "Request failed";
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  { retryOnExpiry = true }: { retryOnExpiry?: boolean } = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  const access = tokens.access();
  if (access) headers.set("Authorization", `Bearer ${access}`);
  if (init.body && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, { ...init, headers });
  } catch {
    // Network-level failure: the API is not running at all.
    throw new ApiError(0, "unreachable");
  }

  // One transparent refresh, then give up — a refresh loop would hammer the API.
  if (response.status === 401 && retryOnExpiry && tokens.refresh()) {
    const renewed = await renew();
    if (renewed) return request<T>(path, init, { retryOnExpiry: false });
  }

  if (!response.ok) throw new ApiError(response.status, await parseError(response));
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

async function renew(): Promise<boolean> {
  try {
    const response = await fetch(`${API_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: tokens.refresh() }),
    });
    if (!response.ok) {
      tokens.clear();
      return false;
    }
    const data = await response.json();
    tokens.set(data.access_token, data.refresh_token);
    return true;
  } catch {
    return false;
  }
}

export const api = {
  health: () => request<Health>("/health"),

  register: async (payload: {
    email: string;
    password: string;
    name: string;
    preferred_language: string;
    user_type?: string;
  }) => {
    const data = await request<{ access_token: string; refresh_token: string }>("/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    tokens.set(data.access_token, data.refresh_token);
  },

  login: async (email: string, password: string) => {
    const data = await request<{ access_token: string; refresh_token: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    tokens.set(data.access_token, data.refresh_token);
  },

  me: () => request<User>("/auth/me"),
  setInterests: (interests: Record<string, number>) =>
    request<User>("/auth/me/interests", { method: "PUT", body: JSON.stringify({ interests }) }),

  sites: (params: Record<string, string | number | boolean> = {}) => {
    const query = new URLSearchParams(
      Object.entries(params).map(([k, v]) => [k, String(v)]),
    ).toString();
    return request<Site[]>(`/sites${query ? `?${query}` : ""}`);
  },
  site: (slug: string) => request<Site>(`/sites/${slug}`),
  recommended: (limit = 8) => request<Recommendation[]>(`/sites/recommended?limit=${limit}`),
  recordEvent: (slug: string, kind: string) =>
    request<void>(`/sites/${slug}/events?kind=${kind}`, { method: "POST" }),

  ask: (payload: {
    question: string;
    language: string;
    level?: string;
    conversation_id?: string | null;
  }) => request<Answer>("/guide/ask", { method: "POST", body: JSON.stringify(payload) }),

  identifyPhoto: (file: File, language: string, fix?: GeolocationCoordinates | null) => {
    const form = new FormData();
    form.append("file", file);
    form.append("language", language);
    if (fix) {
      form.append("latitude", String(fix.latitude));
      form.append("longitude", String(fix.longitude));
    }
    return request<VisionResult>("/guide/vision", { method: "POST", body: form });
  },

  generateItinerary: (payload: { query: string; language: string; save?: boolean }) =>
    request<Itinerary>("/itineraries/generate", { method: "POST", body: JSON.stringify(payload) }),
  myItineraries: () =>
    request<{ id: string; title: string; days: number; stops: number; language: string }[]>(
      "/itineraries",
    ),
  itinerary: (id: string) => request<Itinerary>(`/itineraries/${id}`),

  services: (params: Record<string, string | boolean> = {}) => {
    const query = new URLSearchParams(
      Object.entries(params).map(([k, v]) => [k, String(v)]),
    ).toString();
    return request<ServiceOffer[]>(`/services${query ? `?${query}` : ""}`);
  },
  book: (payload: { service_id: string; scheduled_for: string; party_size: number }) =>
    request<Booking>("/bookings", { method: "POST", body: JSON.stringify(payload) }),
  bookings: () => request<Booking[]>("/bookings"),

  products: (params: Record<string, string | boolean> = {}) => {
    const query = new URLSearchParams(
      Object.entries(params).map(([k, v]) => [k, String(v)]),
    ).toString();
    return request<Product[]>(`/marketplace/products${query ? `?${query}` : ""}`);
  },
  order: (product_id: string, quantity = 1) =>
    request<Order>("/marketplace/orders", {
      method: "POST",
      body: JSON.stringify({ product_id, quantity }),
    }),
  orders: () => request<Order[]>("/marketplace/orders"),

  practical: (region: string, language: string) =>
    request<{
      region: string;
      emergency: Record<string, string>;
      transport: Record<string, string>[];
      etiquette: string[];
      weekend: string;
      currency: string;
    }>(`/practical?region=${encodeURIComponent(region)}&language=${language}`),

  dashboard: () => request<Dashboard>("/dashboard"),
};
