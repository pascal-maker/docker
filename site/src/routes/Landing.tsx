import { Button, ButtonLink } from "@refactor-agent/ui";

export function Landing() {
  const requestAccessUrl = getRequestAccessUrl();
  const canRequest = requestAccessUrl && requestAccessUrl !== "#";

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4">
      <main className="max-w-2xl text-center space-y-8">
        <h1 className="text-4xl font-bold tracking-tight text-slate-900 sm:text-5xl">
          Refactorum
        </h1>
        <p className="text-lg text-slate-600">
          Agentic code refactoring with confidence.
        </p>
        <div>
          {canRequest ? (
            <ButtonLink
              href={requestAccessUrl}
              className="text-base px-6 py-3"
            >
              Request access
            </ButtonLink>
          ) : (
            <Button className="text-base px-6 py-3" disabled>
              Request access
            </Button>
          )}
        </div>
      </main>
    </div>
  );
}

function getRequestAccessUrl(): string {
  const clientId = import.meta.env.VITE_GITHUB_OAUTH_CLIENT_ID ?? "";
  const callbackUrl = import.meta.env.VITE_AUTH_CALLBACK_URL ?? "";
  if (!clientId || !callbackUrl) return "#";
  const params = new URLSearchParams({
    client_id: clientId,
    redirect_uri: callbackUrl,
    scope: "read:user user:email",
  });
  return `https://github.com/login/oauth/authorize?${params.toString()}`;
}
