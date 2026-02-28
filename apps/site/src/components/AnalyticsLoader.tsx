import { useEffect } from "react";
import { useConsent } from "@/hooks/useConsent.ts";
import { initAnalytics } from "@/lib/analytics.ts";

/**
 * Loads Firebase Analytics only when user has accepted cookies.
 * Renders nothing.
 */
export function AnalyticsLoader() {
  const { consent } = useConsent();

  useEffect(() => {
    if (consent === "accepted") {
      initAnalytics();
    }
  }, [consent]);

  return null;
}
