/**
 * Consent-gated analytics. Loads Firebase/GA4 only when user has accepted cookies.
 */

declare global {
  interface Window {
    gtag?: (...args: unknown[]) => void;
    dataLayer?: unknown[];
  }
}

const MEASUREMENT_ID = import.meta.env.VITE_FIREBASE_MEASUREMENT_ID as
  | string
  | undefined;

let initialized = false;

export function initAnalytics(): void {
  if (!MEASUREMENT_ID || initialized) return;

  initialized = true;
  window.dataLayer = window.dataLayer ?? [];

  function gtag(...args: unknown[]): void {
    window.dataLayer?.push(args);
  }
  window.gtag = gtag;

  const script = document.createElement("script");
  script.async = true;
  script.src = `https://www.googletagmanager.com/gtag/js?id=${MEASUREMENT_ID}`;
  document.head.appendChild(script);

  gtag("js", new Date());
  gtag("config", MEASUREMENT_ID, { send_page_view: true });
}

export function isAnalyticsConfigured(): boolean {
  return Boolean(MEASUREMENT_ID);
}
