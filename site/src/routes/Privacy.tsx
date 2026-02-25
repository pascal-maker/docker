import { useEffect } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@refactor-agent/ui";

const privacyUrl = import.meta.env.VITE_PRIVACY_POLICY_URL as
  | string
  | undefined;
const contactEmail = import.meta.env.VITE_IMPRINT_EMAIL as string | undefined;

export function Privacy() {
  useEffect(() => {
    if (privacyUrl != null && privacyUrl !== "") {
      window.location.replace(privacyUrl);
    }
  }, []);

  if (privacyUrl != null && privacyUrl !== "") {
    return (
      <div className="min-h-screen px-4 py-12 max-w-3xl mx-auto">
        <p className="text-slate-600">Redirecting to privacy policy…</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen px-4 py-12 max-w-3xl mx-auto">
      <Card>
        <CardHeader>
          <CardTitle>Privacy Policy</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-slate-600">
            Privacy policy will be available soon.
            {contactEmail != null && contactEmail !== "" && (
              <>
                {" "}
                For questions, contact{" "}
                <a
                  href={`mailto:${contactEmail}`}
                  className="text-blue-600 hover:underline"
                >
                  {contactEmail}
                </a>
                .
              </>
            )}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
