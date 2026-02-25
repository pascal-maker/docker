import { useEffect } from "react";
import { useConsent } from "@/hooks/useConsent";
import { initAnalytics } from "@/lib/analytics";

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
