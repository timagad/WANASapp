"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { ApiError, api, tokens, type Health, type User } from "@/lib/api";
import { type Locale, type Messages } from "@/lib/i18n";

type WanasContext = {
  locale: Locale;
  t: Messages;
  dir: "rtl" | "ltr";
  user: User | null;
  health: Health | null;
  apiReachable: boolean;
  refreshUser: () => Promise<void>;
  signOut: () => void;
};

const Ctx = createContext<WanasContext | null>(null);

export function Providers({
  locale,
  messages,
  dir,
  children,
}: {
  locale: Locale;
  messages: Messages;
  dir: "rtl" | "ltr";
  children: React.ReactNode;
}) {
  const [user, setUser] = useState<User | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [apiReachable, setApiReachable] = useState(true);

  const refreshUser = useCallback(async () => {
    if (!tokens.access()) {
      setUser(null);
      return;
    }
    try {
      setUser(await api.me());
    } catch (error) {
      // A dead session should log the user out, but a dead network should not.
      if (error instanceof ApiError && error.status !== 0) tokens.clear();
      setUser(null);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    api
      .health()
      .then((value) => {
        if (cancelled) return;
        setHealth(value);
        setApiReachable(true);
      })
      .catch(() => !cancelled && setApiReachable(false));
    void refreshUser();
    return () => {
      cancelled = true;
    };
  }, [refreshUser]);

  const signOut = useCallback(() => {
    tokens.clear();
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ locale, t: messages, dir, user, health, apiReachable, refreshUser, signOut }),
    [locale, messages, dir, user, health, apiReachable, refreshUser, signOut],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useWanas(): WanasContext {
  const value = useContext(Ctx);
  if (!value) throw new Error("useWanas must be used inside <Providers>");
  return value;
}
