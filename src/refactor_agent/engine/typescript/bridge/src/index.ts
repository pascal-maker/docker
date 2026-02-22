import { createInterface } from "readline";
import { Project, Node, type Identifier, type SourceFile } from "ts-morph";

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

let project: Project | null = null;
let sourceFile: SourceFile | null = null;
const VIRTUAL_FILE = "/virtual/source.ts";

// ---------------------------------------------------------------------------
// JSON-RPC types
// ---------------------------------------------------------------------------

interface Request {
  id: number;
  method: string;
  params: Record<string, unknown>;
}

interface CollisionInfo {
  location: string;
  kind: string;
}

// ---------------------------------------------------------------------------
// Handlers
// ---------------------------------------------------------------------------

function handleInit(params: Record<string, unknown>): { ok: true } {
  const source = params["source"];
  if (typeof source !== "string") {
    throw new Error("params.source must be a string");
  }
  project = new Project({ useInMemoryFileSystem: true });
  sourceFile = project.createSourceFile(VIRTUAL_FILE, source);
  return { ok: true };
}

function handleGetSkeleton(): string {
  if (!sourceFile) throw new Error("No source file loaded (call init first)");

  const parts: string[] = [];

  for (const fn of sourceFile.getFunctions()) {
    const line = fn.getStartLineNumber();
    const args = fn.getParameters().map((p) => p.getName());
    const calls = new Set<string>();
    const assigns = new Set<string>();

    fn.forEachDescendant((node) => {
      if (Node.isCallExpression(node)) {
        const expr = node.getExpression();
        if (Node.isIdentifier(expr)) {
          calls.add(expr.getText());
        }
      }
      if (Node.isVariableDeclaration(node)) {
        assigns.add(node.getName());
      }
    });

    const lines = [`FunctionDef '${fn.getName() ?? "(anonymous)"}' (line ${line})`];
    if (args.length > 0) lines.push(`  args: ${args.join(", ")}`);
    if (calls.size > 0) lines.push(`  calls: ${JSON.stringify([...calls].sort())}`);
    if (assigns.size > 0) lines.push(`  assigns: ${JSON.stringify([...assigns].sort())}`);
    parts.push(lines.join("\n"));
  }

  for (const cls of sourceFile.getClasses()) {
    const line = cls.getStartLineNumber();
    const calls = new Set<string>();
    const assigns = new Set<string>();

    cls.forEachDescendant((node) => {
      if (Node.isCallExpression(node)) {
        const expr = node.getExpression();
        if (Node.isIdentifier(expr)) {
          calls.add(expr.getText());
        }
      }
      if (Node.isVariableDeclaration(node)) {
        assigns.add(node.getName());
      }
    });

    const lines = [`ClassDef '${cls.getName() ?? "(anonymous)"}' (line ${line})`];
    if (calls.size > 0) lines.push(`  calls: ${JSON.stringify([...calls].sort())}`);
    if (assigns.size > 0) lines.push(`  assigns: ${JSON.stringify([...assigns].sort())}`);
    parts.push(lines.join("\n"));
  }

  return parts.join("\n\n");
}

function handleRenameSymbol(params: Record<string, unknown>): string {
  if (!sourceFile || !project) {
    throw new Error("No source file loaded (call init first)");
  }

  const oldName = params["old_name"];
  const newName = params["new_name"];
  const scopeNode = params["scope_node"] ?? null;

  if (typeof oldName !== "string" || typeof newName !== "string") {
    throw new Error("old_name and new_name must be strings");
  }
  if (scopeNode !== null && typeof scopeNode !== "string") {
    throw new Error("scope_node must be a string or null");
  }

  const identifiers = findRenameableIdentifiers(sourceFile, oldName, scopeNode);
  if (identifiers.length === 0) {
    return `ERROR: symbol '${oldName}' not found in file`;
  }

  // Collect line numbers before renaming (positions shift after rename)
  const renamedLines = identifiers.map((id) => id.getStartLineNumber());
  renamedLines.sort((a, b) => a - b);

  // ts-morph's .rename() on one declaration propagates to all references,
  // so we only need to rename once per unique declaration.
  const first = identifiers[0]!;
  first.rename(newName);

  const scopeNote = scopeNode
    ? ` within scope '${scopeNode}'`
    : " (file-wide)";
  return (
    `Renamed '${oldName}' → '${newName}'${scopeNote}: ` +
    `${renamedLines.length} occurrence(s) at lines [${renamedLines.join(", ")}]`
  );
}

function findRenameableIdentifiers(
  sf: SourceFile,
  name: string,
  scopeNode: string | null,
): Identifier[] {
  const searchRoot: Node = scopeNode ? findScope(sf, scopeNode) ?? sf : sf;

  // First pass: find declaration identifiers (the defining occurrence)
  const declarations: Identifier[] = [];
  const usages: Identifier[] = [];

  searchRoot.forEachDescendant((node) => {
    if (!Node.isIdentifier(node)) return;
    if (node.getText() !== name) return;

    const parent = node.getParent();
    if (!parent) return;

    const isDecl =
      Node.isFunctionDeclaration(parent) ||
      Node.isClassDeclaration(parent) ||
      Node.isInterfaceDeclaration(parent) ||
      Node.isTypeAliasDeclaration(parent) ||
      Node.isEnumDeclaration(parent) ||
      Node.isVariableDeclaration(parent) ||
      Node.isParameterDeclaration(parent) ||
      Node.isPropertyDeclaration(parent) ||
      Node.isPropertySignature(parent) ||
      Node.isMethodDeclaration(parent) ||
      Node.isMethodSignature(parent) ||
      Node.isImportSpecifier(parent) ||
      Node.isExportSpecifier(parent);

    if (isDecl) {
      declarations.push(node);
    } else {
      usages.push(node);
    }
  });

  // One declaration rename propagates to all references
  if (declarations.length > 0) return declarations.slice(0, 1);

  // Fallback: rename from a usage identifier
  return usages.slice(0, 1);
}

function findScope(sf: SourceFile, name: string): Node | null {
  for (const fn of sf.getFunctions()) {
    if (fn.getName() === name) return fn;
  }
  for (const cls of sf.getClasses()) {
    if (cls.getName() === name) return cls;
  }
  return null;
}

function handleCheckNameCollisions(
  params: Record<string, unknown>,
): CollisionInfo[] {
  if (!sourceFile) {
    throw new Error("No source file loaded (call init first)");
  }

  const newName = params["new_name"];
  if (typeof newName !== "string") {
    throw new Error("new_name must be a string");
  }

  const collisions: CollisionInfo[] = [];

  for (const fn of sourceFile.getFunctions()) {
    if (fn.getName() === newName) {
      collisions.push({
        location: `line ${fn.getStartLineNumber()}`,
        kind: "FunctionDef",
      });
    }
  }
  for (const cls of sourceFile.getClasses()) {
    if (cls.getName() === newName) {
      collisions.push({
        location: `line ${cls.getStartLineNumber()}`,
        kind: "ClassDef",
      });
    }
  }
  for (const vs of sourceFile.getVariableStatements()) {
    for (const decl of vs.getDeclarations()) {
      if (decl.getName() === newName) {
        collisions.push({
          location: `line ${decl.getStartLineNumber()}`,
          kind: "VariableDeclaration",
        });
      }
    }
  }

  return collisions;
}

function handleToSource(): string {
  if (!sourceFile) {
    throw new Error("No source file loaded (call init first)");
  }
  return sourceFile.getFullText();
}

function handleExtractFunction(): string {
  return (
    "ERROR: extract_function is not yet implemented for TypeScript; " +
    "only rename_symbol is supported."
  );
}

// ---------------------------------------------------------------------------
// Dispatch
// ---------------------------------------------------------------------------

type HandlerResult = unknown;

const handlers: Record<
  string,
  (params: Record<string, unknown>) => HandlerResult
> = {
  init: handleInit,
  get_skeleton: handleGetSkeleton,
  rename_symbol: handleRenameSymbol,
  check_name_collisions: handleCheckNameCollisions,
  to_source: handleToSource,
  extract_function: handleExtractFunction,
};

function dispatch(request: Request): { id: number; result?: unknown; error?: string } {
  const handler = handlers[request.method];
  if (!handler) {
    return { id: request.id, error: `Unknown method: ${request.method}` };
  }
  try {
    const result = handler(request.params ?? {});
    return { id: request.id, result };
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return { id: request.id, error: message };
  }
}

// ---------------------------------------------------------------------------
// stdin/stdout JSON-RPC loop
// ---------------------------------------------------------------------------

const rl = createInterface({ input: process.stdin });

rl.on("line", (line: string) => {
  const trimmed = line.trim();
  if (!trimmed) return;

  let request: Request;
  try {
    request = JSON.parse(trimmed) as Request;
  } catch {
    const errorResp = { id: -1, error: "Invalid JSON" };
    process.stdout.write(JSON.stringify(errorResp) + "\n");
    return;
  }

  const response = dispatch(request);
  process.stdout.write(JSON.stringify(response) + "\n");
});

rl.on("close", () => {
  process.exit(0);
});
