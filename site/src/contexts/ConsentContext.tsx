/* eslint-disable react-refresh/only-export-components -- Context + Provider pattern; hook in hooks/useConsent.ts */
import { createContext, useCallback, useEffect, useState } from "react";

const CONSENT_KEY = "refactor-agent-cookie-consent";
const CONSENT_TIMESTAMP_KEY = "refactor-agent-cookie-consent-timestamp";

export type ConsentStatus = "accepted" | "rejected" | null;

interface ConsentContextValue {
  consent: ConsentStatus;
  setConsent: (status: "accepted" | "rejected") => void;
}

export const ConsentContext = createContext<ConsentContextValue | null>(null);

function loadConsent(): ConsentStatus {
  const stored = localStorage.getItem(CONSENT_KEY);
  if (stored === "accepted" || stored === "rejected") return stored;
  return null;
}

export function ConsentProvider({ children }: { children: React.ReactNode }) {
  const [consent, setConsentState] = useState<ConsentStatus>(null);

  useEffect(() => {
    setConsentState(loadConsent());
  }, []);

  const setConsent = useCallback((status: "accepted" | "rejected") => {
    localStorage.setItem(CONSENT_KEY, status);
    localStorage.setItem(CONSENT_TIMESTAMP_KEY, new Date().toISOString());
    setConsentState(status);
  }, []);

  return (
    <ConsentContext.Provider value={{ consent, setConsent }}>
      {children}
    </ConsentContext.Provider>
  );
}
