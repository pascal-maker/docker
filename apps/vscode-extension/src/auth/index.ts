import vscode from "vscode";
import { execSync } from "child_process";
import { StructuredError, SyncStatus } from "../types";
import { RefactorAgentAuthProvider } from "./RefactorAgentAuthProvider";

/** Parse sync/A2A error into structured form. */
export function parseStructuredError(
  statusCode: number,
  text: string
): StructuredError {
  try {
    const data = JSON.parse(text) as { error?: string; detail?: string };
    return {
      statusCode,
      error: data.error,
      detail: data.detail,
      raw: text,
    };
  } catch {
    return { statusCode, raw: text };
  }
}

/** Format auth/status errors into user-friendly messages. */
export function formatAuthMessage(
  err: StructuredError,
  accessRequestUrl: string
): string {
  const { statusCode, detail = "" } = err;
  if (statusCode === 429) {
    return "Rate limit reached. Please try again in a few minutes.";
  }
  if (statusCode === 503 && /auth not configured/i.test(detail)) {
    return "Backend is still being set up. For local dev, ensure GOOGLE_CLOUD_PROJECT is set. For hosted, try again later.";
  }
  if (statusCode === 403) {
    if (/access pending|apply at/i.test(detail)) {
      const urlMatch = detail.match(/Apply at (https?:\/\/\S+)/i);
      const url = urlMatch?.[1] ?? accessRequestUrl;
      return `We're onboarding you! [Request access](${url}) and we'll approve shortly.`;
    }
    if (/access denied|blocked|restricted/i.test(detail)) {
      return "Your access has been restricted. Contact support if you believe this is an error.";
    }
  }
  return err.raw ?? `Error: ${statusCode}`;
}

/** Classify error for status bar. */
export function classifyAuthStatus(err: StructuredError): SyncStatus {
  if (err.statusCode === 429) return "rate_limited";
  if (err.statusCode === 403) {
    if (/access pending|apply at/i.test(err.detail ?? "")) return "pending";
    return "blocked";
  }
  return "error";
}

const A2A_URL_FILE = ".refactor-agent-a2a-url";

/** Get Refactor Agent auth token; fall back to apiKey from settings if user cancels. */
export async function getAuthToken(): Promise<string | undefined> {
  try {
    const session = await vscode.authentication.getSession(
      RefactorAgentAuthProvider.id,
      [],
      { createIfNone: true }
    );
    return session?.accessToken;
  } catch {
    // User cancelled or auth unavailable
  }
  return (
    vscode.workspace
      .getConfiguration("refactorAgent")
      .get<string>("apiKey", "") || undefined
  );
}

/** Get Git remote origin URL for workspace folder, if available. */
export function getGitRepoUrl(
  folder: vscode.WorkspaceFolder
): string | undefined {
  try {
    const url = execSync("git remote get-url origin", {
      cwd: folder.uri.fsPath,
      encoding: "utf8",
    }).trim();
    return url || undefined;
  } catch {
    return undefined;
  }
}

/** A2A base URL: workspace file .refactor-agent-a2a-url (from make infra-a2a-url) overrides settings. */
export async function getA2aBaseUrl(
  folder: vscode.WorkspaceFolder | undefined
): Promise<string> {
  const fromConfig = vscode.workspace
    .getConfiguration("refactorAgent")
    .get<string>("a2aBaseUrl", "http://localhost:9999");
  if (!folder) return fromConfig;
  try {
    const uri = vscode.Uri.joinPath(folder.uri, A2A_URL_FILE);
    const buf = await vscode.workspace.fs.readFile(uri);
    const url = Buffer.from(buf).toString("utf8").trim();
    if (url) return url;
  } catch {
    // file missing or unreadable
  }
  return fromConfig;
}

/** Sync URL: use explicit syncUrl if set, else A2A base URL (same for hosted Cloud Run). */
export async function getSyncUrl(
  folder: vscode.WorkspaceFolder | undefined
): Promise<string> {
  const fromConfig = vscode.workspace
    .getConfiguration("refactorAgent")
    .get<string>("syncUrl", "");
  if (fromConfig && fromConfig.trim()) return fromConfig.trim();
  return getA2aBaseUrl(folder);
}
