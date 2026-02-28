import { useQuery } from "@tanstack/react-query";
import type { IssuesListParams } from "@/types/api.ts";
import { fetchIssuesList, fetchIssueDetail } from "./client.ts";

export function useIssuesList(orgId: string, params: IssuesListParams = {}) {
  return useQuery({
    queryKey: ["issues", orgId, params],
    queryFn: () => fetchIssuesList(orgId, params),
    enabled: orgId.length > 0,
  });
}

export function useIssueDetail(orgId: string, runId: string) {
  return useQuery({
    queryKey: ["issue", orgId, runId],
    queryFn: () => fetchIssueDetail(orgId, runId),
    enabled: orgId.length > 0 && runId.length > 0,
  });
}
