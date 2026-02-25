import { useEffect, useState } from "react";
import { Button } from "@refactor-agent/design-system";
import { useConsent } from "@/hooks/useConsent";

const privacyUrl =
  (import.meta.env.VITE_PRIVACY_POLICY_URL as string | undefined) ?? "/privacy";

export function CookieBanner() {
  const { consent, setConsent } = useConsent();
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (consent === null) setVisible(true);
    else setVisible(false);
  }, [consent]);

  const accept = () => {
    setConsent("accepted");
    setVisible(false);
  };

  const reject = () => {
    setConsent("rejected");
    setVisible(false);
  };

  if (!visible) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 bg-slate-900 text-white px-4 py-4 shadow-lg z-50">
      <div className="max-w-4xl mx-auto flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <p className="text-sm">
          We use cookies for analytics. See our{" "}
          <a
            href={privacyUrl}
            className="underline hover:no-underline"
            target="_blank"
            rel="noopener noreferrer"
          >
            Privacy Policy
          </a>
          .
        </p>
        <div className="flex gap-3 shrink-0">
          <Button
            type="button"
            variant="outline"
            onClick={reject}
            className="border-white text-white bg-transparent hover:bg-slate-800 hover:text-white"
          >
            Reject
          </Button>
          <Button
            type="button"
            variant="default"
            onClick={accept}
            className="bg-white text-slate-900 hover:bg-slate-100"
          >
            Accept
          </Button>
        </div>
      </div>
    </div>
  );
}
