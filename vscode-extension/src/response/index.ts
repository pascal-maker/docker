import vscode from "vscode";

export function getTextFromMessage(
  msg: { parts?: unknown[] } | undefined
): string {
  const parts = msg?.parts ?? [];
  for (const p of parts) {
    if (
      p &&
      typeof p === "object" &&
      "text" in p &&
      typeof (p as { text: string }).text === "string"
    ) {
      return (p as { text: string }).text;
    }
  }
  return "";
}

export function normalizeState(state: string | undefined): string {
  if (!state) return "";
  return state.replace(/-/g, "_");
}

export function extractRenameArtifacts(result: {
  artifacts?: unknown[];
}): { path: string; modified_source: string }[] {
  const out: { path: string; modified_source: string }[] = [];
  const artifacts = result.artifacts ?? [];
  for (const a of artifacts) {
    const art = a as { name?: string; parts?: unknown[] };
    if (art?.name !== "rename-result" || !Array.isArray(art.parts)) continue;
    for (const part of art.parts) {
      if (
        part &&
        typeof part === "object" &&
        ("data" in part || "kind" in part)
      ) {
        const p = part as {
          data?: { path?: string; modified_source?: string };
        };
        const data = p.data;
        if (data?.path != null && data?.modified_source != null) {
          out.push({
            path: String(data.path),
            modified_source: String(data.modified_source),
          });
        }
      }
    }
  }
  return out;
}

export async function applyArtifacts(
  workspaceFolder: vscode.WorkspaceFolder,
  artifacts: { path: string; modified_source: string }[]
): Promise<void> {
  const uris: vscode.Uri[] = [];
  for (const { path: relPath, modified_source } of artifacts) {
    const uri = vscode.Uri.joinPath(workspaceFolder.uri, relPath);
    uris.push(uri);
    await vscode.workspace.fs.writeFile(
      uri,
      new TextEncoder().encode(modified_source)
    );
  }
  const edit = new vscode.WorkspaceEdit();
  for (let i = 0; i < artifacts.length; i++) {
    edit.replace(
      uris[i],
      new vscode.Range(0, 0, 999999, 999999),
      artifacts[i].modified_source
    );
  }
  await vscode.workspace.applyEdit(edit);
  for (const uri of uris) {
    const doc = vscode.workspace.textDocuments.find(
      (d) => d.uri.toString() === uri.toString()
    );
    if (doc?.isDirty) {
      await doc.save();
    }
  }
}
