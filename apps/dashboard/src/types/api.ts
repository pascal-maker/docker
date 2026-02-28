/** API types mirroring backend Pydantic models (dashboard/models.py). */

export interface OperationOut {
  file_path: string;
  op_type: string;
  rationale: string | null;
  sort_order: number;
}

export interface IssueSummary {
  id: string;
  org_id: string;
  repo_id: string;
  branch: string;
  pr_number: number | null;
  preset_id: string;
  goal: string;
  status: string;
  operation_count: number;
  created_at: string;
}

export interface IssueDetail {
  id: string;
  org_id: string;
  repo_id: string;
  branch: string;
  pr_number: number | null;
  preset_id: string;
  goal: string;
  status: string;
  operation_count: number;
  created_at: string;
  operations: OperationOut[];
}

export interface IssuesListResponse {
  items: IssueSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface IssuesListParams {
  repo_id?: string | undefined;
  preset_id?: string | undefined;
  since?: string | undefined;
  until?: string | undefined;
  limit?: number | undefined;
  offset?: number | undefined;
}
