import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

function getAuthSignInUrl(): string {
  const clientId =
    import.meta.env.VITE_GITHUB_APP_CLIENT_ID ??
    import.meta.env.VITE_GITHUB_OAUTH_CLIENT_ID ??
    "";
  const callbackUrl = import.meta.env.VITE_AUTH_CALLBACK_URL ?? "";
  if (!clientId || !callbackUrl) return "/";
  const params = new URLSearchParams({
    client_id: clientId,
    redirect_uri: callbackUrl,
    state: "return:vscode",
  });
  return `https://github.com/login/oauth/authorize?${params.toString()}`;
}

/** Redirects to GitHub OAuth with state=return:vscode for extension auth flow. */
export function AuthSignIn() {
  const navigate = useNavigate();

  useEffect(() => {
    const url = getAuthSignInUrl();
    if (url === "/") {
      void navigate("/", { replace: true });
      return;
    }
    window.location.href = url;
  }, [navigate]);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4">
      <p className="text-slate-600">Redirecting to GitHub...</p>
    </div>
  );
}
