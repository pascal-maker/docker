const privacyUrl =
  (import.meta.env.VITE_PRIVACY_POLICY_URL as string | undefined) ?? "/privacy";
const termsUrl =
  (import.meta.env.VITE_TERMS_URL as string | undefined) ?? "/terms";

export function Footer() {
  return (
    <footer className="border-t border-slate-200 py-6 mt-auto">
      <div className="max-w-4xl mx-auto px-4 flex flex-wrap gap-x-6 gap-y-2 text-sm text-slate-600">
        <a
          href={privacyUrl}
          className="hover:text-slate-900"
          {...(privacyUrl.startsWith("http")
            ? { target: "_blank", rel: "noopener noreferrer" }
            : {})}
        >
          Privacy
        </a>
        <a
          href={termsUrl}
          className="hover:text-slate-900"
          {...(termsUrl.startsWith("http")
            ? { target: "_blank", rel: "noopener noreferrer" }
            : {})}
        >
          Terms
        </a>
        <a href="/imprint" className="hover:text-slate-900">
          Imprint
        </a>
      </div>
    </footer>
  );
}
