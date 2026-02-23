import { execSync } from "child_process";
import * as vscode from "vscode";

const PENDING_STATE_KEY = "refactorAgent.pendingReply";
const GITHUB_SCOPES = ["repo", "read:user"];
const CONVERSATIONS_KEY = "refactorAgent.conversations";
const CURRENT_CONVERSATION_ID_KEY = "refactorAgent.currentConversationId";
const MAX_CONVERSATIONS = 50;

interface PendingReply {
  taskId: string;
  contextId: string;
  workspaceUri: string;
}

interface ChatMessage {
  role: "user" | "agent";
  kind?: string;
  text: string;
}

interface Conversation {
  id: string;
  title: string;
  messages: ChatMessage[];
}

type SyncStatus = "ok" | "error" | "unknown";

interface SyncStatusUpdater {
  update(status: SyncStatus, message?: string): void;
}

const A2A_URL_FILE = ".refactor-agent-a2a-url";

/** Get GitHub OAuth token; fall back to apiKey from settings if user cancels. */
async function getAuthToken(): Promise<string | undefined> {
  try {
    const session = await vscode.authentication.getSession(
      "github",
      GITHUB_SCOPES,
      {
        createIfNone: true,
      }
    );
    return session?.accessToken;
  } catch {
    // User cancelled or GitHub auth unavailable
  }
  return (
    vscode.workspace
      .getConfiguration("refactorAgent")
      .get<string>("apiKey", "") || undefined
  );
}

/** Get Git remote origin URL for workspace folder, if available. */
function getGitRepoUrl(folder: vscode.WorkspaceFolder): string | undefined {
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
async function getA2aBaseUrl(
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
async function getSyncUrl(
  folder: vscode.WorkspaceFolder | undefined
): Promise<string> {
  const fromConfig = vscode.workspace
    .getConfiguration("refactorAgent")
    .get<string>("syncUrl", "");
  if (fromConfig && fromConfig.trim()) return fromConfig.trim();
  return getA2aBaseUrl(folder);
}

/** Parse "rename X to Y", "rename X Y", or JSON { old_name, new_name }. */
function parseRenameIntentFromPrompt(
  prompt: string
): { old_name: string; new_name: string } | null {
  const trimmed = prompt.trim();
  try {
    const data = JSON.parse(trimmed) as {
      old_name?: string;
      new_name?: string;
    };
    if (
      typeof data?.old_name === "string" &&
      typeof data?.new_name === "string"
    ) {
      return { old_name: data.old_name, new_name: data.new_name };
    }
  } catch {
    // not JSON
  }
  const toMatch =
    trimmed.match(/rename\s+(\S+)\s+to\s+(\S+)/i) ||
    trimmed.match(/rename\s+(\S+)\s+(\S+)/i);
  if (toMatch) {
    return { old_name: toMatch[1], new_name: toMatch[2] };
  }
  return null;
}

type Engine = "python" | "typescript";

function getGlobPatterns(engine: Engine): string[] {
  if (engine === "typescript") {
    return ["**/*.ts", "**/*.tsx"];
  }
  return ["**/*.py"];
}

async function gatherWorkspaceFiles(
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
async function gatherDirtyFiles(
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

async function pushWorkspaceViaSync(
  syncUrl: string,
  files: { path: string; content: string }[],
  options?: { authToken?: string; repoUrl?: string }
): Promise<string | null> {
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
    return `Sync failed ${res.status}: ${text}`;
  }
  return null;
}

async function sendA2AMessage(
  baseUrl: string,
  apiKey: string | undefined,
  payload: object
): Promise<{ response: unknown; error?: string }> {
  const url = baseUrl.replace(/\/$/, "");
  const messageText = JSON.stringify(payload);
  const body = {
    jsonrpc: "2.0",
    id: globalThis.crypto.randomUUID(),
    method: "message/send",
    params: {
      message: {
        kind: "message",
        role: "user",
        messageId: globalThis.crypto.randomUUID(),
        parts: [{ kind: "text", text: messageText }],
      },
    },
  };
  return postA2A(url, apiKey, body);
}

async function sendA2AResume(
  baseUrl: string,
  apiKey: string | undefined,
  taskId: string,
  contextId: string,
  userReplyText: string
): Promise<{ response: unknown; error?: string }> {
  const url = baseUrl.replace(/\/$/, "");
  const body = {
    jsonrpc: "2.0",
    id: globalThis.crypto.randomUUID(),
    method: "message/send",
    params: {
      message: {
        kind: "message",
        role: "user",
        messageId: globalThis.crypto.randomUUID(),
        taskId,
        contextId,
        parts: [{ kind: "text", text: userReplyText }],
      },
    },
  };
  return postA2A(url, apiKey, body);
}

async function postA2A(
  url: string,
  apiKey: string | undefined,
  body: object
): Promise<{ response: unknown; error?: string }> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (apiKey) {
    headers["Authorization"] = `Bearer ${apiKey}`;
  }
  try {
    const res = await fetch(url, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    });
    const data = (await res.json()) as {
      result?: Record<string, unknown>;
      error?: { message?: string };
    };
    if (data.error) {
      return {
        response: data,
        error: data.error.message ?? JSON.stringify(data.error),
      };
    }
    return { response: data.result ?? data };
  } catch (e) {
    return { response: {}, error: e instanceof Error ? e.message : String(e) };
  }
}

function getTextFromMessage(msg: { parts?: unknown[] } | undefined): string {
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

function normalizeState(state: string | undefined): string {
  if (!state) return "";
  return state.replace(/-/g, "_");
}

function extractRenameArtifacts(result: {
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

async function applyArtifacts(
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

function getWebviewContent(nonce: string): string {
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'nonce-${nonce}'; style-src 'unsafe-inline';">
  <style>
    html, body { height: 100%; min-height: 100vh; margin: 0; padding: 0; box-sizing: border-box; overflow: hidden; }
    body { font-family: var(--vscode-font-family); font-size: var(--vscode-font-size); color: var(--vscode-foreground); display: flex; flex-direction: column; padding: 8px; padding-bottom: 60px; }
    .sync-status { margin-bottom: 8px; font-size: 12px; flex-shrink: 0; }
    .sync-ok { color: var(--vscode-testing-iconPassed); }
    .sync-err { color: var(--vscode-testing-iconFailed); }
    .sync-unknown { color: var(--vscode-descriptionForeground); }
    #messages { flex: 1; min-height: 0; overflow-y: auto; padding: 8px; font-size: 12px; }
    .msg { margin: 6px 0; padding: 6px 8px; border-radius: 4px; }
    .msg.user { background: var(--vscode-input-background); margin-left: 16px; }
    .msg.agent { background: var(--vscode-editor-inactiveSelectionBackground); margin-right: 16px; }
    .msg.progress { color: var(--vscode-descriptionForeground); }
    .msg.error { color: var(--vscode-errorForeground); }
    #messages pre, #messages code { font-family: var(--vscode-editor-font-family); font-size: 12px; }
    #messages code { background: var(--vscode-textCodeBlock-background); padding: 1px 4px; border-radius: 3px; }
    #messages pre { overflow-x: auto; padding: 8px; margin: 6px 0; }
    #messages pre code { padding: 0; background: transparent; }
    .conversation-row { margin-bottom: 8px; display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
    .conversation-row select { flex: 1; padding: 4px 8px; font: inherit; background: var(--vscode-input-background); color: var(--vscode-input-foreground); border: 1px solid var(--vscode-input-border); border-radius: 4px; }
    .chatbox { position: fixed; bottom: 0; left: 0; right: 0; border: 1px solid var(--vscode-input-border); border-radius: 8px 8px 0 0; background: var(--vscode-input-background); padding: 10px 12px; display: flex; gap: 8px; align-items: flex-end; margin: 0 8px 8px 8px; }
    .chatbox:focus-within { border-color: var(--vscode-focusBorder); outline: 1px solid var(--vscode-focusBorder); outline-offset: -1px; }
    #chatInput { flex: 1; padding: 8px 10px; border: none; background: transparent; color: var(--vscode-input-foreground); font: inherit; resize: none; min-height: 20px; max-height: 120px; }
    #chatInput::placeholder { color: var(--vscode-input-placeholderForeground); }
    #chatInput:focus { outline: none; }
    #sendBtn { flex-shrink: 0; width: 32px; height: 32px; padding: 0; border: none; border-radius: 6px; background: var(--vscode-button-background); color: var(--vscode-button-foreground); cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 16px; line-height: 1; }
    #sendBtn:hover { background: var(--vscode-button-hoverBackground); }
    #sendBtn:disabled { opacity: 0.5; cursor: not-allowed; }
  </style>
</head>
<body>
  <div class="sync-status" id="syncStatus"><span class="sync-unknown">Sync: not checked</span></div>
  <div class="conversation-row">
    <select id="conversationSelect" aria-label="Conversation">
      <option value="">New chat</option>
    </select>
  </div>
  <div id="messages"></div>
  <form id="chatForm" class="chatbox">
    <textarea id="chatInput" rows="1" placeholder="e.g. rename foo to bar or paste JSON" aria-label="Refactor request"></textarea>
    <button type="submit" id="sendBtn" title="Send" aria-label="Send">&#8593;</button>
  </form>
  <script nonce="${nonce}">
    (function() {
      function log() { try { console.log.apply(console, ['[Refactor Agent]'].concat(Array.prototype.slice.call(arguments))); } catch (e) {} }
      function logErr() { try { console.error.apply(console, ['[Refactor Agent]'].concat(Array.prototype.slice.call(arguments))); } catch (e) {} }
    const vscode = acquireVsCodeApi();
    const chatForm = document.getElementById('chatForm');
    const chatInput = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendBtn');
    const messages = document.getElementById('messages');
    const syncStatus = document.getElementById('syncStatus');
    const conversationSelect = document.getElementById('conversationSelect');
    log('Webview script loaded. messages=', !!messages, 'chatForm=', !!chatForm);

    function escapeHtml(s) {
      return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }
    function renderMarkdown(text) {
      text = (text != null && typeof text !== 'string') ? String(text) : (text || '');
      if (!text) return '';
      let out = escapeHtml(text);
      out = out.replace(/\\\\n/g, '\\n');
      const lines = out.split('\\n');
      const result = [];
      let i = 0;
      while (i < lines.length) {
        const line = lines[i];
        const fence = line.match(/^\\x60\\x60\\x60(\\w*)$/);
        if (fence) {
          const lang = fence[1] || '';
          const block = [];
          i++;
          while (i < lines.length && lines[i] !== '\\x60\\x60\\x60') {
            block.push(lines[i]);
            i++;
          }
          if (i < lines.length) i++;
          result.push('<pre><code class="' + escapeHtml(lang) + '">' + block.join('\\n') + '</code></pre>');
          continue;
        }
        let ln = line;
        ln = ln.replace(/\\*\\*([^*]+)\\*\\*/g, '<strong>$1</strong>');
        ln = ln.replace(/\\*([^*]+)\\*/g, '<em>$1</em>');
        ln = ln.replace(/\\x60([^\\x60]+)\\x60/g, '<code>$1</code>');
        result.push(ln + '<br>');
        i++;
      }
      return result.join('\\n');
    }

    function appendMessage(role, kind, text, useMarkdown) {
      if (!messages) return;
      const el = document.createElement('div');
      el.className = 'msg ' + (role || 'agent') + (kind ? ' ' + kind : '');
      const safeText = (text != null && typeof text !== 'string') ? String(text) : (text || '');
      if (useMarkdown && (role === 'agent' || role === 'user')) {
        el.innerHTML = renderMarkdown(safeText);
      } else {
        el.textContent = safeText;
      }
      messages.appendChild(el);
      messages.scrollTop = messages.scrollHeight;
    }

    function submit() {
      const text = chatInput.value.trim();
      if (!text) return;
      appendMessage('user', '', text, false);
      chatInput.value = '';
      chatInput.style.height = 'auto';
      sendBtn.disabled = true;
      vscode.postMessage({ type: 'submit', text: text });
    }

    conversationSelect.addEventListener('change', () => {
      const val = conversationSelect.value;
      if (val === '') {
        vscode.postMessage({ type: 'newChat' });
      } else {
        vscode.postMessage({ type: 'selectConversation', id: val });
      }
    });

    chatForm.addEventListener('submit', (e) => {
      e.preventDefault();
      submit();
    });

    chatInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        submit();
      }
    });

    window.addEventListener('message', (event) => {
      const msg = event.data;
      log('message received', msg && msg.type, msg && msg.type === 'append' ? '(append)' : msg && msg.type === 'restore' ? 'restore convs=' + (msg.conversations && msg.conversations.length) + ' msgs=' + (msg.messages && msg.messages.length) : '');
      if (!msg || !msg.type) return;
      if (msg.type === 'restore') {
        const list = Array.isArray(msg.conversations) ? msg.conversations : [];
        const currentId = msg.currentId != null ? msg.currentId : null;
        const msgs = Array.isArray(msg.messages) ? msg.messages : [];
        if (conversationSelect) conversationSelect.innerHTML = '<option value="">New chat</option>';
        list.forEach(function(c) {
          if (!c || typeof c.id !== 'string') return;
          const opt = document.createElement('option');
          opt.value = c.id;
          opt.textContent = (c.title != null ? String(c.title) : 'Chat') || 'Chat';
          if (c.id === currentId) opt.selected = true;
          conversationSelect && conversationSelect.appendChild(opt);
        });
        if (messages) messages.innerHTML = '';
        msgs.forEach(function(m) {
          try {
            appendMessage(m && m.role, m && m.kind, m && m.text, true);
          } catch (err) {
            logErr('restore appendMessage error', err);
            appendMessage('agent', 'error', String(m && m.text || 'Invalid message'), false);
          }
        });
        if (messages) messages.scrollTop = messages.scrollHeight;
      } else if (msg.type === 'append') {
        try {
          appendMessage(msg.role || 'agent', msg.kind, msg.text, true);
        } catch (err) {
          logErr('append error', err, 'msg.text type=', typeof msg.text);
          if (messages) {
            const fallback = document.createElement('div');
            fallback.className = 'msg agent error';
            fallback.textContent = typeof msg.text === 'string' ? msg.text : 'Message could not be displayed';
            messages.appendChild(fallback);
          }
        }
      } else if (msg.type === 'submitDone') {
        if (sendBtn) sendBtn.disabled = false;
      } else if (msg.type === 'syncStatus') {
        if (syncStatus) {
          const span = document.createElement('span');
          if (msg.status === 'ok') { span.className = 'sync-ok'; span.textContent = 'Sync: OK'; }
          else if (msg.status === 'error') { span.className = 'sync-err'; span.textContent = 'Sync: ' + (msg.message || 'Error'); }
          else { span.className = 'sync-unknown'; span.textContent = 'Sync: not checked'; }
          syncStatus.innerHTML = '';
          syncStatus.appendChild(span);
        }
      }
    });

    log('posting ready');
    vscode.postMessage({ type: 'ready' });
    })();
  </script>
</body>
</html>`;
}

function getNonce(): string {
  let out = "";
  const pool = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
  for (let i = 0; i < 32; i++) {
    out += pool.charAt(Math.floor(Math.random() * pool.length));
  }
  return out;
}

class RefactorViewProvider implements vscode.WebviewViewProvider {
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

      if (resume) {
        append("progress", "Sending your reply to the agent…");
        const { response, error } = await sendA2AResume(
          a2aBaseUrl,
          authToken,
          resume.taskId,
          resume.contextId,
          resume.replyText
        );
        globalState.update(PENDING_STATE_KEY, undefined);
        if (error) {
          append("error", `Error: ${error}`);
          post("submitDone");
          return;
        }
        await this.handleResponse(
          response as Record<string, unknown>,
          folder,
          globalState,
          append,
          post,
          a2aBaseUrl,
          authToken
        );
        post("submitDone");
        return;
      }

      const intent =
        promptText != null ? parseRenameIntentFromPrompt(promptText) : null;
      if (!intent) {
        append(
          "message",
          'Say something like: rename foo to bar, or paste JSON: {"old_name": "foo", "new_name": "bar"}'
        );
        post("submitDone");
        return;
      }

      const engine = vscode.workspace
        .getConfiguration("refactorAgent")
        .get<Engine>("engine", "python");

      const repoUrl = getGitRepoUrl(folder);
      append(
        "progress",
        repoUrl ? "Gathering dirty files…" : "Gathering workspace files…"
      );
      const files = repoUrl
        ? await gatherDirtyFiles(folder, engine)
        : await gatherWorkspaceFiles(folder, engine);
      if (files.length === 0 && !repoUrl) {
        const msg =
          engine === "typescript"
            ? "No TypeScript files found in the workspace."
            : "No Python files found in the workspace.";
        append("error", msg);
        post("submitDone");
        return;
      }

      append("progress", "Pushing workspace to sync service…");
      const syncErr = await pushWorkspaceViaSync(syncUrl, files, {
        authToken,
        repoUrl,
      });
      if (syncErr) {
        this._syncStatus.update("error", syncErr);
        append("error", `Sync failed: ${syncErr}`);
        post("submitDone");
        return;
      }
      this._syncStatus.update("ok");
      post("syncStatus", { status: "ok" });

      append("progress", "Sending refactor request to A2A…");
      const payload = {
        old_name: intent.old_name,
        new_name: intent.new_name,
        use_replica: true,
        language: engine,
        prompt: promptText,
      };
      const { response, error } = await sendA2AMessage(
        a2aBaseUrl,
        authToken,
        payload
      );
      if (error) {
        append("error", `A2A error: ${error}`);
        post("submitDone");
        return;
      }

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

function createSyncStatusBarItem(): SyncStatusUpdater & {
  item: vscode.StatusBarItem;
} {
  const item = vscode.window.createStatusBarItem(
    vscode.StatusBarAlignment.Left,
    100
  );
  item.show();
  return {
    item,
    update(status: SyncStatus, message?: string) {
      if (status === "ok") {
        item.text = "$(check) Refactor Agent: Sync OK";
        item.tooltip = "Sync service reachable";
        item.backgroundColor = undefined;
      } else if (status === "error") {
        item.text = "$(close) Refactor Agent: Sync error";
        item.tooltip = message ?? "Sync failed";
        item.backgroundColor = new vscode.ThemeColor(
          "statusBarItem.errorBackground"
        );
      } else {
        item.text = "$(circle-large-outline) Refactor Agent: Sync";
        item.tooltip = "Sync not checked yet";
        item.backgroundColor = undefined;
      }
    },
  };
}

export function activate(extContext: vscode.ExtensionContext): void {
  const syncStatus = createSyncStatusBarItem();
  extContext.subscriptions.push(syncStatus.item);

  const provider = new RefactorViewProvider(extContext, syncStatus);
  extContext.subscriptions.push(
    vscode.window.registerWebviewViewProvider(
      "refactorAgent-refactorView",
      provider
    )
  );

  extContext.subscriptions.push(
    vscode.commands.registerCommand("refactorAgent.focusView", () => {
      vscode.commands.executeCommand("refactorAgent-refactorView.focus");
    })
  );

  extContext.subscriptions.push(
    vscode.commands.registerCommand("refactorAgent.openWebviewDevTools", () => {
      void vscode.commands.executeCommand(
        "workbench.action.webview.openDeveloperTools"
      );
    })
  );
}

export function deactivate(): void {}
