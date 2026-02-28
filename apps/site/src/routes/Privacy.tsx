import { useEffect } from "react";

const privacyUrl = import.meta.env.VITE_PRIVACY_POLICY_URL as
  | string
  | undefined;

export function Privacy() {
  useEffect(() => {
    if (privacyUrl != null && privacyUrl !== "") {
      window.location.replace(privacyUrl);
    } else {
      window.location.replace("/privacy.html");
    }
  }, []);

  return (
    <div className="min-h-screen px-4 py-12 max-w-3xl mx-auto">
      <p className="text-slate-600">Redirecting to privacy policy…</p>
    </div>
  );
}
