const API_BASE = "";

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${String(res.status)}: ${text || res.statusText}`);
  }
  return res.json() as Promise<T>;
}

import type { IssuesListParams, IssuesListResponse, IssueDetail } from "@/types/api";

export async function fetchIssuesList(
  orgId: string,
  params: IssuesListParams = {}
): Promise<IssuesListResponse> {
  const sp = new URLSearchParams();
  if (params.repo_id !== undefined && params.repo_id !== "")
    sp.set("repo_id", params.repo_id);
  if (params.preset_id !== undefined && params.preset_id !== "")
    sp.set("preset_id", params.preset_id);
  if (params.since !== undefined && params.since !== "")
    sp.set("since", params.since);
  if (params.until !== undefined && params.until !== "")
    sp.set("until", params.until);
  if (params.limit !== undefined) sp.set("limit", String(params.limit));
  if (params.offset !== undefined) sp.set("offset", String(params.offset));
  const qs = sp.toString();
  const url = `/api/orgs/${encodeURIComponent(orgId)}/issues${qs ? `?${qs}` : ""}`;
  return getJson(url);
}

export async function fetchIssueDetail(
  orgId: string,
  runId: string
): Promise<IssueDetail> {
  const url = `/api/orgs/${encodeURIComponent(orgId)}/issues/${encodeURIComponent(runId)}`;
  return getJson(url);
}
