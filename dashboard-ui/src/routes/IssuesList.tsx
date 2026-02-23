import { useState, useMemo } from "react";
import { Link, useParams } from "react-router-dom";
import { useIssuesList } from "@/api/hooks";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const PAGE_SIZE = 50;

export function IssuesList() {
  const { orgId } = useParams<{ orgId: string }>();
  const [repoId, setRepoId] = useState("");
  const [presetId, setPresetId] = useState("");
  const [since, setSince] = useState("");
  const [until, setUntil] = useState("");
  const [offset, setOffset] = useState(0);

  const params = useMemo((): import("@/types/api").IssuesListParams => {
    const p: import("@/types/api").IssuesListParams = {
      limit: PAGE_SIZE,
      offset,
    };
    const r = repoId.trim();
    const pr = presetId.trim();
    const si = since.trim();
    const un = until.trim();
    if (r) p.repo_id = r;
    if (pr) p.preset_id = pr;
    if (si) p.since = si;
    if (un) p.until = un;
    return p;
  }, [repoId, presetId, since, until, offset]);

  const { data, isLoading, error } = useIssuesList(orgId ?? "", params);

  if (orgId === undefined) {
    return (
      <div className="p-6">
        <p className="text-red-600">Missing org ID</p>
      </div>
    );
  }

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const hasPrev = offset > 0;
  const hasNext = offset + items.length < total;

  return (
    <div className="min-h-screen p-6">
      <nav className="mb-6">
        <Link to="/" className="text-slate-600 hover:text-slate-900 text-sm">
          ← Dashboard
        </Link>
      </nav>
      <Card>
        <CardHeader className="pb-4">
          <CardTitle>Issues — {orgId}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <form
            className="flex flex-wrap gap-4 items-end"
            onSubmit={(e) => {
              e.preventDefault();
            }}
          >
            <label className="flex flex-col gap-1 text-sm">
              Repo
              <Input
                placeholder="org/repo"
                value={repoId}
                onChange={(e) => {
                  setRepoId(e.target.value);
                  setOffset(0);
                }}
              />
            </label>
            <label className="flex flex-col gap-1 text-sm">
              Preset
              <Input
                placeholder="preset id"
                value={presetId}
                onChange={(e) => {
                  setPresetId(e.target.value);
                  setOffset(0);
                }}
              />
            </label>
            <label className="flex flex-col gap-1 text-sm">
              Since
              <Input
                placeholder="ISO date"
                value={since}
                onChange={(e) => {
                  setSince(e.target.value);
                  setOffset(0);
                }}
              />
            </label>
            <label className="flex flex-col gap-1 text-sm">
              Until
              <Input
                placeholder="ISO date"
                value={until}
                onChange={(e) => {
                  setUntil(e.target.value);
                  setOffset(0);
                }}
              />
            </label>
          </form>

          {error && (
            <p className="text-red-600 text-sm">
              {error instanceof Error ? error.message : "Failed to load"}
            </p>
          )}
          {isLoading && <p className="text-slate-600 text-sm">Loading…</p>}

          {!isLoading && !error && (
            <>
              <div className="overflow-x-auto rounded-md border border-slate-200">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 bg-slate-50">
                      <th className="text-left p-3 font-medium">Repo</th>
                      <th className="text-left p-3 font-medium">Branch</th>
                      <th className="text-left p-3 font-medium">PR</th>
                      <th className="text-left p-3 font-medium">Preset</th>
                      <th className="text-left p-3 font-medium">Goal</th>
                      <th className="text-left p-3 font-medium"># Ops</th>
                      <th className="text-left p-3 font-medium">Date</th>
                      <th className="text-left p-3 font-medium"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.length === 0 ? (
                      <tr>
                        <td colSpan={8} className="p-4 text-slate-500">
                          No issues found.
                        </td>
                      </tr>
                    ) : (
                      items.map((item) => (
                        <tr
                          key={item.id}
                          className="border-b border-slate-100 hover:bg-slate-50"
                        >
                          <td className="p-3">{item.repo_id}</td>
                          <td className="p-3">{item.branch}</td>
                          <td className="p-3">
                            {item.pr_number != null
                              ? `#${String(item.pr_number)}`
                              : "—"}
                          </td>
                          <td className="p-3">{item.preset_id}</td>
                          <td
                            className="p-3 max-w-xs truncate"
                            title={item.goal}
                          >
                            {item.goal}
                          </td>
                          <td className="p-3">{item.operation_count}</td>
                          <td className="p-3 text-slate-600">
                            {formatDate(item.created_at)}
                          </td>
                          <td className="p-3">
                            <Link
                              to={`/orgs/${encodeURIComponent(orgId)}/issues/${item.id}`}
                              className="text-slate-700 hover:underline"
                            >
                              Detail
                            </Link>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
              <div className="flex items-center gap-4 text-sm text-slate-600">
                <span>
                  Showing {items.length} of {total}
                </span>
                {hasPrev && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setOffset((o) => Math.max(0, o - PAGE_SIZE));
                    }}
                  >
                    Previous
                  </Button>
                )}
                {hasNext && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setOffset((o) => o + PAGE_SIZE);
                    }}
                  >
                    Next
                  </Button>
                )}
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function formatDate(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleString();
  } catch {
    return iso;
  }
}
