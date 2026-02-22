import { Link, useParams } from "react-router-dom";
import { useIssueDetail } from "@/api/hooks";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function IssueDetail() {
  const { orgId, runId } = useParams<{ orgId: string; runId: string }>();
  const { data: detail, isLoading, error } = useIssueDetail(orgId ?? "", runId ?? "");

  if (orgId === undefined || runId === undefined) {
    return (
      <div className="p-6">
        <p className="text-red-600">Missing org or run ID</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <p className="text-red-600">
          {error instanceof Error ? error.message : "Failed to load"}
        </p>
        <Link to={`/orgs/${encodeURIComponent(orgId)}/issues`} className="text-sm text-slate-600 mt-2 inline-block">
          ← Back to issues
        </Link>
      </div>
    );
  }

  if (isLoading || detail === undefined) {
    return (
      <div className="p-6">
        <p className="text-slate-600">Loading…</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen p-6">
      <nav className="mb-6">
        <Link
          to={`/orgs/${encodeURIComponent(orgId)}/issues`}
          className="text-slate-600 hover:text-slate-900 text-sm"
        >
          ← Back to issues
        </Link>
      </nav>
      <Card>
        <CardHeader>
          <CardTitle className="text-xl">{detail.goal}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-slate-600">
            <strong>Repo</strong> {detail.repo_id} · <strong>Branch</strong>{" "}
            {detail.branch}
            {detail.pr_number != null && (
              <>
                {" "}
                · <strong>PR</strong> #{String(detail.pr_number)}
              </>
            )}
          </p>
          <p className="text-sm text-slate-600">
            <strong>Preset</strong> {detail.preset_id} · <strong>Status</strong>{" "}
            {detail.status} · <strong>Date</strong> {formatDate(detail.created_at)}
          </p>
        </CardContent>
      </Card>
      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="text-lg">
            Suggested operations ({detail.operations.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {detail.operations.length === 0 ? (
            <p className="text-slate-500 text-sm">No operations.</p>
          ) : (
            <ul className="space-y-3">
              {detail.operations.map((op, i) => (
                <li
                  key={`${op.file_path}-${String(i)}`}
                  className="border-b border-slate-100 pb-3 last:border-0 last:pb-0"
                >
                  <p className="font-medium text-slate-900">{op.file_path}</p>
                  <p className="text-sm text-slate-600">
                    <code className="bg-slate-100 px-1 rounded">{op.op_type}</code>
                  </p>
                  {op.rationale != null && op.rationale !== "" && (
                    <p className="text-sm text-slate-500 mt-1">{op.rationale}</p>
                  )}
                </li>
              ))}
            </ul>
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
