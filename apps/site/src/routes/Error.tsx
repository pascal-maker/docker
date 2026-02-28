import { Link } from "react-router-dom";
import { Button } from "@refactor-agent/design-system";

export function Error() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4">
      <main className="max-w-md text-center space-y-6">
        <h1 className="text-2xl font-semibold text-slate-900">
          Something went wrong
        </h1>
        <p className="text-slate-600">
          We couldn&apos;t complete your access request. Please try again later.
        </p>
        <Link to="/">
          <Button variant="outline">Back to home</Button>
        </Link>
      </main>
    </div>
  );
}
