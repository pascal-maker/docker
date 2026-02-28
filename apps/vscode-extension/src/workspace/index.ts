import vscode from "vscode";
import { execSync } from "child_process";
import { Engine, StructuredError } from "../types";
import { parseStructuredError } from "../auth";

function getGlobPatterns(engine: Engine): string[] {
  if (engine === "typescript") {
    return ["**/*.ts", "**/*.tsx"];
  }
  return ["**/*.py"];
}

export async function gatherWorkspaceFiles(
  workspaceFolder: vscode.WorkspaceFolder,
  engine: Engine
): Promise<{ path: string; content: string }[]> {
  const files: { path: string; content: string }[] = [];
  const patterns = getGlobPatterns(engine);
  for (const pattern of patterns) {
    const uris = await vscode.workspace.findFiles(
      new vscode.RelativePattern(workspaceFolder, pattern),
      null,
      2000
    );
    for (const uri of uris) {
      const rel = vscode.workspace.asRelativePath(uri, false);
      const path = rel.replace(/\\/g, "/");
      try {
        const doc = await vscode.workspace.openTextDocument(uri);
        files.push({ path, content: doc.getText() });
      } catch {
        // skip unreadable
      }
    }
  }
  return files;
}

/** Get only modified and untracked files (dirty) via git status. Falls back to all files if not a git repo. */
export async function gatherDirtyFiles(
  workspaceFolder: vscode.WorkspaceFolder,
  engine: Engine
): Promise<{ path: string; content: string }[]> {
  try {
    const statusOut = execSync("git status --porcelain", {
      cwd: workspaceFolder.uri.fsPath,
      encoding: "utf8",
    });
    const patterns = getGlobPatterns(engine);
    const extRe = engine === "typescript" ? /\.(ts|tsx)$/ : /\.py$/;
    const dirtyPaths = new Set<string>();
    for (const line of statusOut.split("\n")) {
      if (!line.trim()) continue;
      const path = line.slice(3).trim().replace(/\\/g, "/");
      if (!extRe.test(path)) continue;
      const matchesPattern = patterns.some((p) => {
        const re = new RegExp(
          "^" + p.replace(/\*\*/g, ".*").replace(/\*/g, "[^/]*") + "$"
        );
        return re.test(path);
      });
      if (matchesPattern) dirtyPaths.add(path);
    }
    const files: { path: string; content: string }[] = [];
    for (const path of dirtyPaths) {
      const uri = vscode.Uri.joinPath(workspaceFolder.uri, path);
      try {
        const doc = await vscode.workspace.openTextDocument(uri);
        files.push({ path, content: doc.getText() });
      } catch {
        // skip unreadable
      }
    }
    if (files.length > 0) return files;
  } catch {
    // Not a git repo or git not available
  }
  return gatherWorkspaceFiles(workspaceFolder, engine);
}

export async function pushWorkspaceViaSync(
  syncUrl: string,
  files: { path: string; content: string }[],
  options?: { authToken?: string; repoUrl?: string }
): Promise<StructuredError | null> {
  const url = syncUrl.replace(/\/$/, "") + "/sync/workspace";
  const body = JSON.stringify({
    files,
    repo_url: options?.repoUrl ?? undefined,
  });
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (options?.authToken) {
    headers["Authorization"] = `Bearer ${options.authToken}`;
  }
  const res = await fetch(url, { method: "POST", headers, body });
  if (!res.ok) {
    const text = await res.text();
    return parseStructuredError(res.status, text);
  }
  return null;
}
