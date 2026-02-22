import { createInterface } from "readline";
import {
  Project,
  Node,
  StructureKind,
  ts,
  type SourceFile,
  type Identifier,
} from "ts-morph";

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

interface ReferenceEntry {
  file: string;
  line: number;
  column: number;
  text: string;
  is_definition: boolean;
}

interface DiagnosticEntry {
  file: string;
  line: number;
  column: number;
  message: string;
  severity: string;
  code: number;
}

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

type Mode = "idle" | "single" | "project";

let mode: Mode = "idle";
let project: Project | null = null;
let singleSourceFile: SourceFile | null = null;
const originalSources = new Map<string, string>();
const VIRTUAL_FILE = "/virtual/source.ts";

// ---------------------------------------------------------------------------
// Param helpers
// ---------------------------------------------------------------------------

function requireString(params: Record<string, unknown>, key: string): string {
  const v = params[key];
  if (typeof v !== "string") {
    throw new Error(`params.${key} must be a string`);
  }
  return v;
}

function optionalString(
  params: Record<string, unknown>,
  key: string,
): string | null {
  const v = params[key];
  if (v === undefined || v === null) return null;
  if (typeof v !== "string") {
    throw new Error(`params.${key} must be a string or null`);
  }
  return v;
}

// ---------------------------------------------------------------------------
// Project helpers
// ---------------------------------------------------------------------------

function requireProject(): Project {
  if (!project) {
    throw new Error("No project loaded (call init or init_project first)");
  }
  return project;
}

function getSourceFile(params: Record<string, unknown>): SourceFile {
  if (mode === "single") {
    if (!singleSourceFile) {
      throw new Error("No source loaded (call init first)");
    }
    return singleSourceFile;
  }
  const filePath = requireString(params, "file_path");
  const p = requireProject();
  const sf = p.getSourceFile(filePath);
  if (!sf) {
    throw new Error(`File not found in project: ${filePath}`);
  }
  return sf;
}

function snapshotSources(): void {
  originalSources.clear();
  for (const sf of requireProject().getSourceFiles()) {
    originalSources.set(sf.getFilePath(), sf.getFullText());
  }
}

// ---------------------------------------------------------------------------
// Node-finding helpers
// ---------------------------------------------------------------------------

function findNamedDeclaration(
  sf: SourceFile,
  name: string,
  kind: string | null = null,
): Node | null {
  if (!kind || kind === "function") {
    const fn = sf.getFunction(name);
    if (fn) return fn;
  }
  if (!kind || kind === "class") {
    const cls = sf.getClass(name);
    if (cls) return cls;
  }
  if (!kind || kind === "interface") {
    const iface = sf.getInterface(name);
    if (iface) return iface;
  }
  if (!kind || kind === "type_alias") {
    const ta = sf.getTypeAlias(name);
    if (ta) return ta;
  }
  if (!kind || kind === "enum") {
    const e = sf.getEnum(name);
    if (e) return e;
  }
  if (!kind || kind === "variable") {
    const v = sf.getVariableDeclaration(name);
    if (v) return v;
  }
  return null;
}

function findRenameableIdentifiers(
  sf: SourceFile,
  name: string,
  scopeNode: string | null,
): Identifier[] {
  const searchRoot: Node = scopeNode ? findScope(sf, scopeNode) ?? sf : sf;
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

  if (declarations.length > 0) return declarations.slice(0, 1);
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

/**
 * Find the first identifier for a named symbol in a source file,
 * preferring declarations over usages.
 */
function findSymbolIdentifier(
  sf: SourceFile,
  name: string,
): Identifier | null {
  const ids = findRenameableIdentifiers(sf, name, null);
  return ids[0] ?? null;
}

// ---------------------------------------------------------------------------
// Handler: init (single-file, backward compat)
// ---------------------------------------------------------------------------

function handleInit(params: Record<string, unknown>): { ok: true } {
  const source = requireString(params, "source");
  project = new Project({ useInMemoryFileSystem: true });
  singleSourceFile = project.createSourceFile(VIRTUAL_FILE, source);
  mode = "single";
  originalSources.clear();
  return { ok: true };
}

// ---------------------------------------------------------------------------
// Handler: init_project (project-level)
// ---------------------------------------------------------------------------

function handleInitProject(
  params: Record<string, unknown>,
): { ok: true; files: string[] } {
  const rootDir = requireString(params, "root_dir");
  const tsconfigPath = optionalString(params, "tsconfig_path");

  if (tsconfigPath) {
    project = new Project({ tsConfigFilePath: tsconfigPath });
  } else {
    project = new Project({
      compilerOptions: {
        target: ts.ScriptTarget.ES2022,
        module: ts.ModuleKind.Node16,
        moduleResolution: ts.ModuleResolutionKind.Node16,
        strict: true,
        esModuleInterop: true,
      },
    });
    project.addSourceFilesAtPaths(`${rootDir}/**/*.{ts,tsx}`);
  }

  mode = "project";
  singleSourceFile = null;
  snapshotSources();

  const files = project
    .getSourceFiles()
    .map((sf) => sf.getFilePath());
  return { ok: true, files };
}

// ---------------------------------------------------------------------------
// Handler: get_skeleton
// ---------------------------------------------------------------------------

function buildSkeletonForFile(sf: SourceFile): string {
  const parts: string[] = [];

  for (const fn of sf.getFunctions()) {
    const line = fn.getStartLineNumber();
    const args = fn.getParameters().map((p) => p.getName());
    const calls = new Set<string>();
    const assigns = new Set<string>();
    fn.forEachDescendant((node) => {
      if (Node.isCallExpression(node)) {
        const expr = node.getExpression();
        if (Node.isIdentifier(expr)) calls.add(expr.getText());
      }
      if (Node.isVariableDeclaration(node)) assigns.add(node.getName());
    });
    const lines = [
      `FunctionDef '${fn.getName() ?? "(anonymous)"}' (line ${line})`,
    ];
    if (args.length > 0) lines.push(`  args: ${args.join(", ")}`);
    if (calls.size > 0) {
      lines.push(`  calls: ${JSON.stringify([...calls].sort())}`);
    }
    if (assigns.size > 0) {
      lines.push(`  assigns: ${JSON.stringify([...assigns].sort())}`);
    }
    parts.push(lines.join("\n"));
  }

  for (const cls of sf.getClasses()) {
    const line = cls.getStartLineNumber();
    const calls = new Set<string>();
    const assigns = new Set<string>();
    cls.forEachDescendant((node) => {
      if (Node.isCallExpression(node)) {
        const expr = node.getExpression();
        if (Node.isIdentifier(expr)) calls.add(expr.getText());
      }
      if (Node.isVariableDeclaration(node)) assigns.add(node.getName());
    });
    const lines = [
      `ClassDef '${cls.getName() ?? "(anonymous)"}' (line ${line})`,
    ];
    if (calls.size > 0) {
      lines.push(`  calls: ${JSON.stringify([...calls].sort())}`);
    }
    if (assigns.size > 0) {
      lines.push(`  assigns: ${JSON.stringify([...assigns].sort())}`);
    }
    parts.push(lines.join("\n"));
  }

  return parts.join("\n\n");
}

function handleGetSkeleton(params: Record<string, unknown>): string {
  const sf = getSourceFile(params);
  return buildSkeletonForFile(sf);
}

// ---------------------------------------------------------------------------
// Handler: rename_symbol
// ---------------------------------------------------------------------------

function handleRenameSymbol(params: Record<string, unknown>): object {
  const p = requireProject();
  const oldName = requireString(params, "old_name");
  const newName = requireString(params, "new_name");
  const scopeNode = optionalString(params, "scope_node");
  const sf = getSourceFile(params);

  const identifiers = findRenameableIdentifiers(sf, oldName, scopeNode);
  if (identifiers.length === 0) {
    return { summary: `ERROR: symbol '${oldName}' not found in file` };
  }

  const renamedLines = identifiers.map((id) => id.getStartLineNumber());
  renamedLines.sort((a, b) => a - b);

  const first = identifiers[0]!;
  first.rename(newName);

  const scopeNote = scopeNode
    ? ` within scope '${scopeNode}'`
    : " (file-wide)";
  const summary =
    `Renamed '${oldName}' → '${newName}'${scopeNote}: ` +
    `${renamedLines.length} occurrence(s) at ` +
    `lines [${renamedLines.join(", ")}]`;

  const changedFiles = getChangedFilesList(p);
  return { summary, changed_files: changedFiles };
}

// ---------------------------------------------------------------------------
// Handler: find_references
// ---------------------------------------------------------------------------

function handleFindReferences(
  params: Record<string, unknown>,
): ReferenceEntry[] {
  const sf = getSourceFile(params);
  const symbolName = requireString(params, "symbol_name");

  const identifier = findSymbolIdentifier(sf, symbolName);
  if (!identifier) {
    throw new Error(`Symbol '${symbolName}' not found in file`);
  }

  const referencedSymbols = identifier.findReferences();
  const entries: ReferenceEntry[] = [];

  for (const refSymbol of referencedSymbols) {
    const def = refSymbol.getDefinition();
    entries.push({
      file: def.getSourceFile().getFilePath(),
      line: def.getTextSpan().getStart(),
      column: 0,
      text: def.getNode().getText().slice(0, 80),
      is_definition: true,
    });
    for (const ref of refSymbol.getReferences()) {
      const refSf = ref.getSourceFile();
      const node = ref.getNode();
      entries.push({
        file: refSf.getFilePath(),
        line: node.getStartLineNumber(),
        column: node.getStart() - node.getStartLinePos(),
        text: node.getText().slice(0, 80),
        is_definition: ref.isDefinition() ?? false,
      });
    }
  }
  return entries;
}

// ---------------------------------------------------------------------------
// Handler: get_source
// ---------------------------------------------------------------------------

function handleGetSource(params: Record<string, unknown>): string {
  const sf = getSourceFile(params);
  return sf.getFullText();
}

// ---------------------------------------------------------------------------
// Handler: get_changed_files
// ---------------------------------------------------------------------------

function getChangedFilesList(p: Project): string[] {
  const changed: string[] = [];
  for (const sf of p.getSourceFiles()) {
    const fp = sf.getFilePath();
    const orig = originalSources.get(fp);
    if (orig === undefined || orig !== sf.getFullText()) {
      changed.push(fp);
    }
  }
  return changed;
}

function handleGetChangedFiles(): { files: string[] } {
  const p = requireProject();
  return { files: getChangedFilesList(p) };
}

// ---------------------------------------------------------------------------
// Handler: remove_node
// ---------------------------------------------------------------------------

function handleRemoveNode(params: Record<string, unknown>): object {
  const sf = getSourceFile(params);
  const symbolName = requireString(params, "symbol_name");
  const kind = optionalString(params, "kind");

  const decl = findNamedDeclaration(sf, symbolName, kind);
  if (!decl) {
    throw new Error(
      `Declaration '${symbolName}' not found` +
        (kind ? ` (kind: ${kind})` : ""),
    );
  }

  const line = decl.getStartLineNumber();
  const nodeKind = decl.getKindName();

  if (Node.isVariableDeclaration(decl)) {
    const declList = decl.getParent();
    if (
      Node.isVariableDeclarationList(declList) &&
      declList.getDeclarations().length === 1
    ) {
      const stmt = declList.getParent();
      if (Node.isVariableStatement(stmt)) {
        stmt.remove();
      } else {
        decl.remove();
      }
    } else {
      decl.remove();
    }
  } else {
    (decl as unknown as { remove(): void }).remove();
  }

  const p = requireProject();
  return {
    summary: `Removed ${nodeKind} '${symbolName}' (was at line ${line})`,
    changed_files: getChangedFilesList(p),
  };
}

// ---------------------------------------------------------------------------
// Handler: move_symbol_to_file
// ---------------------------------------------------------------------------

function updateImportsForMove(
  sourceSf: SourceFile,
  targetSf: SourceFile,
  symbolName: string,
): void {
  const p = requireProject();
  for (const sf of p.getSourceFiles()) {
    if (sf === sourceSf || sf === targetSf) continue;
    for (const imp of sf.getImportDeclarations()) {
      const resolved = imp.getModuleSpecifierSourceFile();
      if (resolved !== sourceSf) continue;

      const named = imp
        .getNamedImports()
        .find((ni) => ni.getName() === symbolName);
      if (!named) continue;

      named.remove();
      if (
        imp.getNamedImports().length === 0 &&
        !imp.getDefaultImport()
      ) {
        imp.remove();
      }

      const existing = sf
        .getImportDeclarations()
        .find(
          (i) => i.getModuleSpecifierSourceFile() === targetSf,
        );
      if (existing) {
        existing.addNamedImport(symbolName);
      } else {
        const specifier =
          sf.getRelativePathAsModuleSpecifierTo(targetSf);
        sf.addImportDeclaration({
          namedImports: [symbolName],
          moduleSpecifier: specifier,
        });
      }
    }
  }
}

function addDeclarationToTarget(
  decl: Node,
  targetSf: SourceFile,
): void {
  if (Node.isFunctionDeclaration(decl)) {
    const s = decl.getStructure();
    if (s.kind === StructureKind.Function) {
      s.isExported = true;
      targetSf.addFunction(s);
    }
  } else if (Node.isClassDeclaration(decl)) {
    const s = decl.getStructure();
    s.isExported = true;
    targetSf.addClass(s);
  } else if (Node.isInterfaceDeclaration(decl)) {
    const s = decl.getStructure();
    s.isExported = true;
    targetSf.addInterface(s);
  } else if (Node.isTypeAliasDeclaration(decl)) {
    const s = decl.getStructure();
    s.isExported = true;
    targetSf.addTypeAlias(s);
  } else if (Node.isEnumDeclaration(decl)) {
    const s = decl.getStructure();
    s.isExported = true;
    targetSf.addEnum(s);
  } else if (Node.isVariableDeclaration(decl)) {
    const declList = decl.getParent();
    if (!Node.isVariableDeclarationList(declList)) {
      throw new Error("Cannot determine variable statement");
    }
    const stmt = declList.getParent();
    if (!Node.isVariableStatement(stmt)) {
      throw new Error("Cannot determine variable statement");
    }
    const s = stmt.getStructure();
    s.isExported = true;
    targetSf.addVariableStatement(s);
  } else {
    throw new Error(
      `Unsupported declaration kind for move: ${decl.getKindName()}`,
    );
  }
}

function removeDeclaration(decl: Node): void {
  if (Node.isVariableDeclaration(decl)) {
    const declList = decl.getParent();
    if (
      Node.isVariableDeclarationList(declList) &&
      declList.getDeclarations().length === 1
    ) {
      const stmt = declList.getParent();
      if (Node.isVariableStatement(stmt)) {
        stmt.remove();
        return;
      }
    }
    decl.remove();
  } else {
    (decl as unknown as { remove(): void }).remove();
  }
}

function handleMoveSymbolToFile(params: Record<string, unknown>): object {
  const p = requireProject();
  const sourceFilePath = requireString(params, "source_file");
  const targetFilePath = requireString(params, "target_file");
  const symbolName = requireString(params, "symbol_name");

  const sourceSf = p.getSourceFile(sourceFilePath);
  if (!sourceSf) {
    throw new Error(`Source file not found: ${sourceFilePath}`);
  }

  let targetSf = p.getSourceFile(targetFilePath);
  if (!targetSf) {
    targetSf = p.createSourceFile(targetFilePath, "");
  }

  const decl = findNamedDeclaration(sourceSf, symbolName);
  if (!decl) {
    throw new Error(
      `Declaration '${symbolName}' not found in ${sourceFilePath}`,
    );
  }

  addDeclarationToTarget(decl, targetSf);
  updateImportsForMove(sourceSf, targetSf, symbolName);
  removeDeclaration(decl);

  try {
    targetSf.fixMissingImports();
  } catch {
    // fixMissingImports can fail in some configurations
  }

  return {
    summary:
      `Moved '${symbolName}' from ` +
      `${sourceFilePath} to ${targetFilePath}`,
    changed_files: getChangedFilesList(p),
  };
}

// ---------------------------------------------------------------------------
// Handler: organize_imports
// ---------------------------------------------------------------------------

function handleOrganizeImports(params: Record<string, unknown>): object {
  const sf = getSourceFile(params);
  sf.organizeImports();
  const p = requireProject();
  return {
    summary: `Organized imports in ${sf.getFilePath()}`,
    changed_files: getChangedFilesList(p),
  };
}

// ---------------------------------------------------------------------------
// Handler: format_file
// ---------------------------------------------------------------------------

function handleFormatFile(params: Record<string, unknown>): object {
  const sf = getSourceFile(params);
  sf.formatText();
  const p = requireProject();
  return {
    summary: `Formatted ${sf.getFilePath()}`,
    changed_files: getChangedFilesList(p),
  };
}

// ---------------------------------------------------------------------------
// Handler: get_diagnostics
// ---------------------------------------------------------------------------

function diagnosticSeverity(category: ts.DiagnosticCategory): string {
  switch (category) {
    case ts.DiagnosticCategory.Error:
      return "error";
    case ts.DiagnosticCategory.Warning:
      return "warning";
    case ts.DiagnosticCategory.Suggestion:
      return "suggestion";
    case ts.DiagnosticCategory.Message:
      return "message";
    default:
      return "unknown";
  }
}

function handleGetDiagnostics(
  params: Record<string, unknown>,
): DiagnosticEntry[] {
  const p = requireProject();
  const filePath = optionalString(params, "file_path");

  const rawDiags = filePath
    ? p
        .getPreEmitDiagnostics()
        .filter(
          (d) => d.getSourceFile()?.getFilePath() === filePath,
        )
    : p.getPreEmitDiagnostics();

  return rawDiags.map((d) => {
    const raw = d.getMessageText();
    const msg =
      typeof raw === "string"
        ? raw
        : ts.flattenDiagnosticMessageText(raw.compilerObject, "\n");
    return {
      file: d.getSourceFile()?.getFilePath() ?? "<unknown>",
      line: d.getLineNumber() ?? 0,
      column: 0,
      message: msg,
      severity: diagnosticSeverity(d.getCategory()),
      code: d.getCode(),
    };
  });
}

// ---------------------------------------------------------------------------
// Handler: check_name_collisions (backward compat)
// ---------------------------------------------------------------------------

function handleCheckNameCollisions(
  params: Record<string, unknown>,
): CollisionInfo[] {
  const sf = getSourceFile(params);
  const newName = requireString(params, "new_name");
  const collisions: CollisionInfo[] = [];

  for (const fn of sf.getFunctions()) {
    if (fn.getName() === newName) {
      collisions.push({
        location: `line ${fn.getStartLineNumber()}`,
        kind: "FunctionDef",
      });
    }
  }
  for (const cls of sf.getClasses()) {
    if (cls.getName() === newName) {
      collisions.push({
        location: `line ${cls.getStartLineNumber()}`,
        kind: "ClassDef",
      });
    }
  }
  for (const vs of sf.getVariableStatements()) {
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

// ---------------------------------------------------------------------------
// Handler: to_source (backward compat for single-file mode)
// ---------------------------------------------------------------------------

function handleToSource(): string {
  if (mode === "single") {
    if (!singleSourceFile) {
      throw new Error("No source file loaded (call init first)");
    }
    return singleSourceFile.getFullText();
  }
  throw new Error("to_source is for single-file mode; use get_source instead");
}

// ---------------------------------------------------------------------------
// Handler: extract_function (stub)
// ---------------------------------------------------------------------------

function handleExtractFunction(): string {
  return (
    "ERROR: extract_function is not yet implemented for TypeScript; " +
    "use rename_symbol, remove_node, and move_symbol_to_file instead."
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
  init_project: handleInitProject,
  get_skeleton: handleGetSkeleton,
  rename_symbol: handleRenameSymbol,
  find_references: handleFindReferences,
  get_source: handleGetSource,
  get_changed_files: handleGetChangedFiles,
  remove_node: handleRemoveNode,
  move_symbol_to_file: handleMoveSymbolToFile,
  organize_imports: handleOrganizeImports,
  format_file: handleFormatFile,
  get_diagnostics: handleGetDiagnostics,
  check_name_collisions: handleCheckNameCollisions,
  to_source: handleToSource,
  extract_function: handleExtractFunction,
};

function dispatch(
  request: Request,
): { id: number; result?: unknown; error?: string } {
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
