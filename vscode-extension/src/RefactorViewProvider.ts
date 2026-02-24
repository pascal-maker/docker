import vscode from "vscode";
import { Conversation, Engine, PendingReply, SyncStatusUpdater } from "./types";
import { getNonce, getWebviewContent } from "./webview";
import {
  CONVERSATIONS_KEY,
  CURRENT_CONVERSATION_ID_KEY,
  MAX_CONVERSATIONS,
  PENDING_STATE_KEY,
} from "./constants";
import {
  classifyAuthStatus,
  formatAuthMessage,
  getA2aBaseUrl,
  getAuthToken,
  getGitRepoUrl,
  getSyncUrl,
} from "./auth";
import { sendA2AMessage, sendA2AResume } from "./a2a";
import { parseRenameIntentFromPrompt } from "./reponse";
import {
  gatherDirtyFiles,
  gatherWorkspaceFiles,
  pushWorkspaceViaSync,
} from "./workspace";
import {
  applyArtifacts,
  extractRenameArtifacts,
  getTextFromMessage,
  normalizeState,
} from "./response";

export class RefactorViewProvider implements vscode.WebviewViewProvider {
  private _view: vscode.WebviewView | undefined;

  constructor(
    private readonly _extContext: vscode.ExtensionContext,
    private readonly _syncStatus: SyncStatusUpdater
  ) {}

  resolveWebviewView(
    webviewView: vscode.WebviewView,
    _context: vscode.WebviewViewResolveContext,
    _token: vscode.CancellationToken
  ): void {
    this._view = webviewView;
    webviewView.webview.options = { enableScripts: true };
    webviewView.webview.html = getWebviewContent(getNonce());

    webviewView.webview.onDidReceiveMessage(async (data: unknown) => {
      const msg = data as { type: string; text?: string; id?: string };
      if (!msg?.type) return;

      const post = (type: string, payload?: Record<string, unknown>) => {
        this._view?.webview.postMessage({ type, ...payload });
      };
      const ws = this._extContext.workspaceState;
      const globalState = this._extContext.globalState;
      const folder = vscode.workspace.workspaceFolders?.[0];

      const getConversations = (): Conversation[] =>
        ws.get<Conversation[]>(CONVERSATIONS_KEY) ?? [];
      const getCurrentId = (): string | undefined =>
        ws.get<string>(CURRENT_CONVERSATION_ID_KEY);
      const persistConversations = (
        list: Conversation[],
        currentId?: string
      ) => {
        const trimmed =
          list.length > MAX_CONVERSATIONS
            ? list.slice(-MAX_CONVERSATIONS)
            : list;
        ws.update(CONVERSATIONS_KEY, trimmed);
        ws.update(CURRENT_CONVERSATION_ID_KEY, currentId ?? undefined);
      };

      if (msg.type === "ready") {
        const conversations = getConversations();
        const currentId = getCurrentId();
        const current = conversations.find((c) => c.id === currentId);
        post("restore", {
          conversations,
          currentId: currentId ?? null,
          messages: current?.messages ?? [],
        });
        return;
      }

      if (msg.type === "selectConversation" && typeof msg.id === "string") {
        ws.update(CURRENT_CONVERSATION_ID_KEY, msg.id);
        const conversations = getConversations();
        const conv = conversations.find((c) => c.id === msg.id);
        post("restore", {
          conversations,
          currentId: msg.id,
          messages: conv?.messages ?? [],
        });
        return;
      }

      if (msg.type === "newChat") {
        ws.update(CURRENT_CONVERSATION_ID_KEY, undefined);
        post("restore", {
          conversations: getConversations(),
          currentId: null,
          messages: [],
        });
        return;
      }

      if (msg.type === "deleteConversation" && typeof msg.id === "string") {
        const conversations = getConversations().filter((c) => c.id !== msg.id);
        const wasCurrent = getCurrentId() === msg.id;
        const newCurrentId = wasCurrent ? undefined : getCurrentId();
        persistConversations(conversations, newCurrentId);
        const conv = newCurrentId
          ? conversations.find((c) => c.id === newCurrentId)
          : undefined;
        post("restore", {
          conversations,
          currentId: newCurrentId ?? null,
          messages: conv?.messages ?? [],
        });
        return;
      }

      if (msg.type === "submit" && typeof msg.text === "string") {
        const conversations = getConversations();
        let currentId = getCurrentId();
        let current = currentId
          ? conversations.find((c) => c.id === currentId)
          : undefined;
        if (!current) {
          currentId = crypto.randomUUID();
          const title = msg.text.slice(0, 40).trim();
          current = {
            id: currentId,
            title: title || "New chat",
            messages: [],
            createdAt: Date.now(),
          };
          conversations.push(current);
          persistConversations(conversations, currentId);
        }
        current.messages.push({ role: "user", text: msg.text });
        persistConversations(conversations, currentId);

        const append = (kind: string, text: string) => {
          post("append", { role: "agent", kind, text });
          const conv = getConversations().find((c) => c.id === currentId);
          if (conv) {
            conv.messages.push({ role: "agent", kind, text });
            persistConversations(getConversations(), currentId);
          }
        };

        const pending = globalState.get<PendingReply>(PENDING_STATE_KEY);
        if (
          pending &&
          folder &&
          pending.workspaceUri === folder.uri.toString()
        ) {
          await this.runRefactor(globalState, folder, post, append, {
            taskId: pending.taskId,
            contextId: pending.contextId,
            replyText: msg.text,
          });
        } else {
          await this.runRefactor(
            globalState,
            folder,
            post,
            append,
            null,
            msg.text
          );
        }
      }
    });
  }

  private async runRefactor(
    globalState: vscode.Memento,
    folder: vscode.WorkspaceFolder | undefined,
    post: (type: string, payload?: Record<string, unknown>) => void,
    append: (kind: string, text: string) => void,
    resume: { taskId: string; contextId: string; replyText: string } | null,
    promptText?: string
  ): Promise<void> {
    const a2aBaseUrl = await getA2aBaseUrl(folder);
    const syncUrl = await getSyncUrl(folder);
    const authToken = await getAuthToken();
    if (!authToken) {
      append(
        "error",
        "Sign in with GitHub required. Use the Accounts menu or set refactorAgent.apiKey for local dev."
      );
      post("submitDone");
      return;
    }

    try {
      if (!folder) {
        append("error", "No workspace folder open.");
        post("submitDone");
        return;
      }

      const accessRequestUrl =
        vscode.workspace
          .getConfiguration("refactorAgent")
          .get<string>("accessRequestUrl", "https://refactor-agent.dev") ??
        "https://refactor-agent.dev";

      if (resume) {
        post("setStatus", { phase: "sending", label: "Sending to agent..." });
        const resumeResult = await sendA2AResume(
          a2aBaseUrl,
          authToken,
          resume.taskId,
          resume.contextId,
          resume.replyText
        );
        globalState.update(PENDING_STATE_KEY, undefined);
        if (resumeResult.error) {
          post("setStatus", { phase: "idle" });
          const friendlyMsg =
            resumeResult.structuredError != null
              ? formatAuthMessage(
                  resumeResult.structuredError,
                  accessRequestUrl
                )
              : `Error: ${resumeResult.error}`;
          const status =
            resumeResult.structuredError != null
              ? classifyAuthStatus(resumeResult.structuredError)
              : "error";
          this._syncStatus.update(status, friendlyMsg);
          post("syncStatus", { status, message: friendlyMsg });
          append("error", friendlyMsg);
          post("submitDone");
          return;
        }
        const { response } = resumeResult;
        post("setStatus", { phase: "idle" });
        await this.handleResponse(
          response as Record<string, unknown>,
          folder,
          globalState,
          append,
          post,
          a2aBaseUrl,
          authToken
        );
        post("setStatus", { phase: "idle" });
        post("submitDone");
        return;
      }

      const engine = vscode.workspace
        .getConfiguration("refactorAgent")
        .get<Engine>("engine", "python");

      const intent =
        promptText != null ? parseRenameIntentFromPrompt(promptText) : null;

      const repoUrl = getGitRepoUrl(folder);
      post("setStatus", { phase: "syncing" });
      const files = repoUrl
        ? await gatherDirtyFiles(folder, engine)
        : await gatherWorkspaceFiles(folder, engine);
      if (files.length === 0 && !repoUrl) {
        post("setStatus", { phase: "idle" });
        const msg =
          engine === "typescript"
            ? "No TypeScript files found in the workspace."
            : "No Python files found in the workspace.";
        append("error", msg);
        post("submitDone");
        return;
      }

      const syncErr = await pushWorkspaceViaSync(syncUrl, files, {
        authToken,
        repoUrl,
      });
      if (syncErr) {
        post("setStatus", { phase: "idle" });
        const status = classifyAuthStatus(syncErr);
        const friendlyMsg = formatAuthMessage(syncErr, accessRequestUrl);
        this._syncStatus.update(status, friendlyMsg);
        post("syncStatus", { status, message: friendlyMsg });
        append("error", friendlyMsg);
        post("submitDone");
        return;
      }
      this._syncStatus.update("ok");
      post("syncStatus", { status: "ok" });

      post("setStatus", { phase: "sending", label: "Sending to agent..." });
      const payload = intent
        ? {
            old_name: intent.old_name,
            new_name: intent.new_name,
            use_replica: true,
            language: engine,
            prompt: promptText,
          }
        : {
            prompt: promptText ?? "",
            use_replica: true,
            language: engine,
          };
      const a2aResult = await sendA2AMessage(a2aBaseUrl, authToken, payload);
      if (a2aResult.error) {
        post("setStatus", { phase: "idle" });
        const structured = a2aResult.structuredError;
        const friendlyMsg =
          structured != null
            ? formatAuthMessage(structured, accessRequestUrl)
            : `A2A error: ${a2aResult.error}`;
        const status =
          structured != null ? classifyAuthStatus(structured) : "error";
        this._syncStatus.update(status, friendlyMsg);
        post("syncStatus", { status, message: friendlyMsg });
        append("error", friendlyMsg);
        post("submitDone");
        return;
      }
      const { response } = a2aResult;

      post("setStatus", { phase: "idle" });
      await this.handleResponse(
        response as Record<string, unknown>,
        folder,
        globalState,
        append,
        post,
        a2aBaseUrl,
        authToken
      );
    } catch (e) {
      post("setStatus", { phase: "idle" });
      append("error", e instanceof Error ? e.message : String(e));
    }
    post("submitDone");
  }

  private async handleResponse(
    res: Record<string, unknown>,
    folder: vscode.WorkspaceFolder,
    globalState: vscode.Memento,
    append: (kind: string, text: string) => void,
    _post: (type: string, payload?: Record<string, unknown>) => void,
    _a2aBaseUrl: string,
    _apiKey: string
  ): Promise<void> {
    const status = res?.status as
      | { state?: string; message?: { parts?: unknown[] } }
      | undefined;
    const rawState = status?.state ?? (res?.state as string | undefined);
    const state = normalizeState(rawState);
    const statusMsg = status?.message ?? status;
    const messageText = getTextFromMessage(
      statusMsg && typeof statusMsg === "object" && "parts" in statusMsg
        ? (statusMsg as { parts?: unknown[] })
        : undefined
    );

    if (state === "input_required") {
      append(
        "message",
        messageText ||
          "Agent needs your input. Reply above (e.g. yes, no, or a new name)."
      );
      globalState.update(PENDING_STATE_KEY, {
        taskId:
          typeof res?.id === "string"
            ? res.id
            : typeof res?.id === "number"
              ? String(res.id)
              : "",
        contextId:
          typeof res?.contextId === "string"
            ? res.contextId
            : typeof res?.contextId === "number"
              ? String(res.contextId)
              : "",
        workspaceUri: folder.uri.toString(),
      });
      return;
    }

    if (state === "completed") {
      const artifacts = extractRenameArtifacts(res);
      if (artifacts.length > 0) {
        try {
          await applyArtifacts(folder, artifacts);
          append(
            "message",
            `Applied changes to ${artifacts.length} file(s).\n\n${messageText || ""}`
          );
        } catch (e) {
          append("error", String(e));
        }
      } else {
        append("message", messageText || "Done.");
      }
      return;
    }

    if (state === "failed") {
      append("error", messageText || "Unknown error");
      return;
    }

    append("message", messageText || `State: ${state}`);
  }
}
