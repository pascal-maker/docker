import { Card, CardHeader, CardTitle, CardContent } from "@refactor-agent/ui";

const name = import.meta.env.VITE_IMPRINT_NAME as string | undefined;
const email = import.meta.env.VITE_IMPRINT_EMAIL as string | undefined;
const address = import.meta.env.VITE_IMPRINT_ADDRESS as string | undefined;
const cbe = import.meta.env.VITE_IMPRINT_CBE as string | undefined;
const vat = import.meta.env.VITE_IMPRINT_VAT as string | undefined;

const privacyUrl =
  (import.meta.env.VITE_PRIVACY_POLICY_URL as string | undefined) ?? "/privacy";
const termsUrl =
  (import.meta.env.VITE_TERMS_URL as string | undefined) ?? "/terms";

export function Imprint() {
  const hasContent = name ?? email ?? address ?? cbe ?? vat;

  return (
    <div className="min-h-screen px-4 py-12 max-w-3xl mx-auto">
      <Card>
        <CardHeader>
          <CardTitle>Imprint / Legal Notice</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {hasContent ? (
            <>
              {name != null && name !== "" && (
                <p className="text-slate-600">
                  <span className="font-medium text-slate-900">Name:</span>{" "}
                  {name}
                </p>
              )}
              {email != null && email !== "" && (
                <p className="text-slate-600">
                  <span className="font-medium text-slate-900">Contact:</span>{" "}
                  <a
                    href={`mailto:${email}`}
                    className="text-blue-600 hover:underline"
                  >
                    {email}
                  </a>
                </p>
              )}
              {address != null && address !== "" && (
                <p className="text-slate-600">
                  <span className="font-medium text-slate-900">Address:</span>{" "}
                  {address}
                </p>
              )}
              {cbe != null && cbe !== "" && (
                <p className="text-slate-600">
                  <span className="font-medium text-slate-900">
                    Company number (CBE):
                  </span>{" "}
                  {cbe}
                </p>
              )}
              {vat != null && vat !== "" && (
                <p className="text-slate-600">
                  <span className="font-medium text-slate-900">VAT number:</span>{" "}
                  {vat}
                </p>
              )}
              <div className="pt-6 border-t border-slate-200">
                <a
                  href={privacyUrl}
                  className="text-blue-600 hover:underline mr-4"
                >
                  Privacy Policy
                </a>
                <a href={termsUrl} className="text-blue-600 hover:underline">
                  Terms of Service
                </a>
              </div>
            </>
          ) : (
            <p className="text-slate-600">
              Contact information will be available soon.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
