import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function OrgSelector() {
  const [orgId, setOrgId] = useState("");
  const navigate = useNavigate();

  function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const trimmed = orgId.trim();
    if (trimmed) {
      void navigate(`/orgs/${encodeURIComponent(trimmed)}/issues`);
    }
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-6">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Refactor issues dashboard</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-slate-600 mb-4">
            View refactor/architecture check results across repos.
          </p>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <label className="text-sm font-medium" htmlFor="org-id">
              Organization ID
            </label>
            <Input
              id="org-id"
              type="text"
              placeholder="e.g. my-org"
              value={orgId}
              onChange={(e) => {
                setOrgId(e.target.value);
              }}
              required
            />
            <Button type="submit">View issues</Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
