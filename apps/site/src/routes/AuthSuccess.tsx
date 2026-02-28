import { useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { Link } from "react-router-dom";
import { Button } from "@refactor-agent/design-system";

const VSCODE_CALLBACK_URI = "vscode://refactor-agent.refactor-agent/callback";

export function AuthSuccess() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");

  useEffect(() => {
    if (!token) return;
    const uri = `${VSCODE_CALLBACK_URI}?token=${encodeURIComponent(token)}`;
    window.location.href = uri;
  }, [token]);

  if (!token) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center px-4">
        <main className="max-w-md text-center space-y-6">
          <h1 className="text-2xl font-semibold text-slate-900">
            No token received
          </h1>
          <p className="text-slate-600">
            The authentication flow did not return a token. Please try signing
            in again from the VS Code extension.
          </p>
          <Link to="/">
            <Button variant="outline">Back to home</Button>
          </Link>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4">
      <main className="max-w-md text-center space-y-6">
        <h1 className="text-2xl font-semibold text-slate-900">
          Opening VS Code...
        </h1>
        <p className="text-slate-600">
          If VS Code does not open automatically,{" "}
          <a
            href={`${VSCODE_CALLBACK_URI}?token=${encodeURIComponent(token)}`}
            className="text-blue-600 hover:underline"
          >
            click here
          </a>
          .
        </p>
      </main>
    </div>
  );
}
