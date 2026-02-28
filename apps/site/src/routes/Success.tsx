import { Link } from "react-router-dom";
import { Button } from "@refactor-agent/design-system";

export function Success() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4">
      <main className="max-w-md text-center space-y-6">
        <h1 className="text-2xl font-semibold text-slate-900">
          Request received
        </h1>
        <p className="text-slate-600">
          We&apos;ll notify you when your access is approved. You can then
          install the VS Code extension and sign in with GitHub.
        </p>
        <Link to="/">
          <Button variant="outline">Back to home</Button>
        </Link>
      </main>
    </div>
  );
}
