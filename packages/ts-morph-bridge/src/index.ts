import * as Sentry from "@sentry/node";
import { createInterface } from "readline";
import { Request } from "./types.js";
import {
  handleCheckNameCollisions,
  handleCreateFile,
  handleExtractFunction,
  handleFindReferences,
  handleFormatFile,
  handleGetChangedFiles,
  handleGetDiagnostics,
  handleGetSkeleton,
  handleGetSource,
  handleInit,
  handleInitProject,
  handleMoveFile,
  handleMoveSymbolToFile,
  handleOrganizeImports,
  handleRemoveNode,
  handleRenameSymbol,
  handleToSource,
} from "./handlers.js";

const sentryDsn = process.env.SENTRY_DSN?.trim();
if (sentryDsn) {
  Sentry.init({ dsn: sentryDsn, tracesSampleRate: 0 });
}

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
  create_file: handleCreateFile,
  move_file: handleMoveFile,
  organize_imports: handleOrganizeImports,
  format_file: handleFormatFile,
  get_diagnostics: handleGetDiagnostics,
  check_name_collisions: handleCheckNameCollisions,
  to_source: handleToSource,
  extract_function: handleExtractFunction,
};

function dispatch(request: Request): {
  id: number;
  result?: unknown;
  error?: string;
} {
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
