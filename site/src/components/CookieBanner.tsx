import { useState, useEffect } from "react";

const CONSENT_KEY = "refactor-agent-cookie-consent";

export function CookieBanner() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const consent = localStorage.getItem(CONSENT_KEY);
    if (consent === null) setVisible(true);
  }, []);

  const accept = () => {
    localStorage.setItem(CONSENT_KEY, "accepted");
    setVisible(false);
  };

  if (!visible) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 bg-slate-900 text-white px-4 py-4 shadow-lg z-50">
      <div className="max-w-4xl mx-auto flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <p className="text-sm">
          We use cookies for essential functionality. By continuing, you agree
          to our{" "}
          <a href="/privacy" className="underline hover:no-underline">
            Privacy Policy
          </a>
          .
        </p>
        <button
          type="button"
          onClick={accept}
          className="shrink-0 px-4 py-2 bg-white text-slate-900 rounded font-medium hover:bg-slate-100"
        >
          Accept
        </button>
      </div>
    </div>
  );
}
