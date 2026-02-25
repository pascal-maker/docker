export function Privacy() {
  return (
    <div className="min-h-screen px-4 py-12 max-w-3xl mx-auto">
      <h1 className="text-3xl font-bold text-slate-900 mb-6">Privacy Policy</h1>
      <p className="text-slate-600 mb-4">
        Copy your privacy policy from a template. Suggested sources:
      </p>
      <ul className="list-disc list-inside text-slate-600 space-y-2 mb-8">
        <li>
          <a
            href="https://gdpr.eu/privacy-notice"
            target="_blank"
            rel="noreferrer"
            className="text-blue-600 hover:underline"
          >
            GDPR.eu template
          </a>
        </li>
        <li>
          <a
            href="https://www.iubenda.com/en/privacy-and-cookie-policy-generator"
            target="_blank"
            rel="noreferrer"
            className="text-blue-600 hover:underline"
          >
            iubenda
          </a>
        </li>
        <li>
          <a
            href="https://termly.io"
            target="_blank"
            rel="noreferrer"
            className="text-blue-600 hover:underline"
          >
            Termly
          </a>
        </li>
      </ul>
      <p className="text-sm text-slate-500">
        Replace this placeholder with your actual privacy policy content.
      </p>
    </div>
  );
}
