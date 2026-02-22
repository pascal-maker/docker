"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const PENDING_STATE_KEY = "refactorAgent.pendingReply";
/** Parse "rename X to Y" or JSON { old_name, new_name }. */
function parseRenameIntent(oldName, newName) {
    const o = oldName?.trim() ?? "";
    const n = newName?.trim() ?? "";
    if (o && n)
        return { old_name: o, new_name: n };
    return null;
}
async function gatherWorkspaceFiles(workspaceFolder) {
    const files = [];
    const pyUris = await vscode.workspace.findFiles(new vscode.RelativePattern(workspaceFolder, "**/*.py"), null, 2000);
    for (const uri of pyUris) {
        const rel = vscode.workspace.asRelativePath(uri, false);
        const path = rel.replace(/\\/g, "/");
        try {
            const doc = await vscode.workspace.openTextDocument(uri);
            files.push({ path, content: doc.getText() });
        }
        catch {
            // skip unreadable
        }
    }
    return files;
}
async function pushWorkspaceViaSync(syncUrl, files) {
    const url = syncUrl.replace(/\/$/, "") + "/sync/workspace";
    const body = JSON.stringify({ files });
    const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body,
    });
    if (!res.ok) {
        const text = await res.text();
        return `Sync failed ${res.status}: ${text}`;
    }
    return null;
}
async function sendA2AMessage(baseUrl, apiKey, payload) {
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
async function sendA2AResume(baseUrl, apiKey, taskId, contextId, userReplyText) {
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
async function postA2A(url, apiKey, body) {
    const headers = {
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
        const data = (await res.json());
        if (data.error) {
            return {
                response: data,
                error: data.error.message ?? JSON.stringify(data.error),
            };
        }
        return { response: data.result ?? data };
    }
    catch (e) {
        return { response: {}, error: e instanceof Error ? e.message : String(e) };
    }
}
function getTextFromMessage(msg) {
    const parts = msg?.parts ?? [];
    for (const p of parts) {
        if (p &&
            typeof p === "object" &&
            "text" in p &&
            typeof p.text === "string") {
            return p.text;
        }
    }
    return "";
}
function normalizeState(state) {
    if (!state)
        return "";
    return state.replace(/-/g, "_");
}
function extractRenameArtifacts(result) {
    const out = [];
    const artifacts = result.artifacts ?? [];
    for (const a of artifacts) {
        const art = a;
        if (art?.name !== "rename-result" || !Array.isArray(art.parts))
            continue;
        for (const part of art.parts) {
            if (part &&
                typeof part === "object" &&
                ("data" in part || "kind" in part)) {
                const p = part;
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
async function applyArtifacts(workspaceFolder, artifacts) {
    const edit = new vscode.WorkspaceEdit();
    for (const { path: relPath, modified_source } of artifacts) {
        const uri = vscode.Uri.joinPath(workspaceFolder.uri, relPath);
        edit.replace(uri, new vscode.Range(0, 0, 999999, 999999), modified_source);
    }
    await vscode.workspace.applyEdit(edit);
}
function getWebviewContent(nonce) {
    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'nonce-${nonce}'; style-src 'unsafe-inline';">
  <style>
    body { font-family: var(--vscode-font-family); font-size: var(--vscode-font-size); padding: 8px; margin: 0; color: var(--vscode-foreground); }
    .sync-status { margin-bottom: 8px; font-size: 12px; }
    .sync-ok { color: var(--vscode-testing-iconPassed); }
    .sync-err { color: var(--vscode-testing-iconFailed); }
    .sync-unknown { color: var(--vscode-descriptionForeground); }
    form { display: flex; flex-direction: column; gap: 6px; margin-bottom: 12px; }
    input, button { padding: 6px 10px; }
    button { cursor: pointer; background: var(--vscode-button-background); color: var(--vscode-button-foreground); border: none; }
    button:hover { background: var(--vscode-button-hoverBackground); }
    #messages { max-height: 300px; overflow-y: auto; border: 1px solid var(--vscode-panel-border); padding: 8px; font-size: 12px; }
    .msg { margin: 4px 0; }
    .msg.progress { color: var(--vscode-descriptionForeground); }
    .msg.error { color: var(--vscode-errorForeground); }
  </style>
</head>
<body>
  <div class="sync-status" id="syncStatus"><span class="sync-unknown">Sync: not checked</span></div>
  <div id="renameForm">
    <form id="form">
      <input type="text" id="oldName" placeholder="Old symbol name" />
      <input type="text" id="newName" placeholder="New symbol name" />
      <button type="submit" id="submitBtn">Rename</button>
    </form>
  </div>
  <div id="replyForm" style="display:none;">
    <form id="replyFormEl">
      <input type="text" id="replyInput" placeholder="Your reply (e.g. yes, no, or new name)" />
      <button type="submit" id="replyBtn">Send reply</button>
    </form>
  </div>
  <div id="messages"></div>
  <script nonce="${nonce}">
    const vscode = acquireVsCodeApi();
    const form = document.getElementById('form');
    const oldName = document.getElementById('oldName');
    const newName = document.getElementById('newName');
    const submitBtn = document.getElementById('submitBtn');
    const messages = document.getElementById('messages');
    const syncStatus = document.getElementById('syncStatus');
    const renameForm = document.getElementById('renameForm');
    const replyForm = document.getElementById('replyForm');
    const replyFormEl = document.getElementById('replyFormEl');
    const replyInput = document.getElementById('replyInput');
    const replyBtn = document.getElementById('replyBtn');

    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const o = oldName.value.trim();
      const n = newName.value.trim();
      if (!o || !n) return;
      submitBtn.disabled = true;
      vscode.postMessage({ type: 'submit', oldName: o, newName: n });
    });

    replyFormEl.addEventListener('submit', (e) => {
      e.preventDefault();
      const t = replyInput.value.trim();
      if (!t) return;
      replyBtn.disabled = true;
      vscode.postMessage({ type: 'reply', text: t });
    });

    window.addEventListener('message', (event) => {
      const msg = event.data;
      if (msg.type === 'append') {
        const el = document.createElement('div');
        el.className = 'msg ' + (msg.kind || '');
        el.textContent = msg.text || '';
        messages.appendChild(el);
        messages.scrollTop = messages.scrollHeight;
      } else if (msg.type === 'submitDone') {
        submitBtn.disabled = false;
        replyBtn.disabled = false;
      } else if (msg.type === 'syncStatus') {
        const span = document.createElement('span');
        if (msg.status === 'ok') { span.className = 'sync-ok'; span.textContent = 'Sync: OK'; }
        else if (msg.status === 'error') { span.className = 'sync-err'; span.textContent = 'Sync: ' + (msg.message || 'Error'); }
        else { span.className = 'sync-unknown'; span.textContent = 'Sync: not checked'; }
        syncStatus.innerHTML = '';
        syncStatus.appendChild(span);
      } else if (msg.type === 'setReplyMode') {
        const reply = msg.active === true;
        renameForm.style.display = reply ? 'none' : 'block';
        replyForm.style.display = reply ? 'block' : 'none';
        if (reply) replyInput.value = '';
      }
    });
  </script>
</body>
</html>`;
}
function getNonce() {
    let out = "";
    const pool = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
    for (let i = 0; i < 32; i++) {
        out += pool.charAt(Math.floor(Math.random() * pool.length));
    }
    return out;
}
class RefactorViewProvider {
    _extContext;
    _syncStatus;
    _view;
    constructor(_extContext, _syncStatus) {
        this._extContext = _extContext;
        this._syncStatus = _syncStatus;
    }
    resolveWebviewView(webviewView, _context, _token) {
        this._view = webviewView;
        webviewView.webview.options = { enableScripts: true };
        webviewView.webview.html = getWebviewContent(getNonce());
        webviewView.webview.onDidReceiveMessage(async (data) => {
            const msg = data;
            if (!msg?.type)
                return;
            const post = (type, payload) => {
                this._view?.webview.postMessage({ type, ...payload });
            };
            const append = (kind, text) => {
                post("append", { kind, text });
            };
            const globalState = this._extContext.globalState;
            const folder = vscode.workspace.workspaceFolders?.[0];
            if (msg.type === "submit" && msg.oldName != null && msg.newName != null) {
                await this.runRefactor(globalState, folder, post, append, null, msg.oldName, msg.newName);
            }
            else if (msg.type === "reply" && typeof msg.text === "string") {
                const pending = globalState.get(PENDING_STATE_KEY);
                if (!folder || !pending || pending.workspaceUri !== folder.uri.toString()) {
                    append("error", "No pending reply for this workspace.");
                    post("submitDone");
                    return;
                }
                await this.runRefactor(globalState, folder, post, append, { taskId: pending.taskId, contextId: pending.contextId, replyText: msg.text }, "", "");
            }
        });
    }
    async runRefactor(globalState, folder, post, append, resume, oldName, newName) {
        const a2aBaseUrl = vscode.workspace
            .getConfiguration("refactorAgent")
            .get("a2aBaseUrl", "http://localhost:9999");
        const syncUrl = vscode.workspace
            .getConfiguration("refactorAgent")
            .get("syncUrl", "http://localhost:8765");
        const apiKey = vscode.workspace
            .getConfiguration("refactorAgent")
            .get("apiKey", "");
        try {
            if (!folder) {
                append("error", "No workspace folder open.");
                post("submitDone");
                return;
            }
            if (resume) {
                append("progress", "Sending your reply to the agent…");
                const { response, error } = await sendA2AResume(a2aBaseUrl, apiKey || undefined, resume.taskId, resume.contextId, resume.replyText);
                globalState.update(PENDING_STATE_KEY, undefined);
                if (error) {
                    append("error", `Error: ${error}`);
                    post("submitDone");
                    return;
                }
                await this.handleResponse(response, folder, globalState, append, post, a2aBaseUrl, apiKey);
                post("submitDone");
                return;
            }
            const intent = parseRenameIntent(oldName, newName);
            if (!intent) {
                append("error", "Enter both old and new symbol names.");
                post("submitDone");
                return;
            }
            append("progress", "Gathering workspace files…");
            const files = await gatherWorkspaceFiles(folder);
            if (files.length === 0) {
                append("error", "No Python files found in the workspace.");
                post("submitDone");
                return;
            }
            append("progress", "Pushing workspace to sync service…");
            const syncErr = await pushWorkspaceViaSync(syncUrl, files);
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
            };
            const { response, error } = await sendA2AMessage(a2aBaseUrl, apiKey || undefined, payload);
            if (error) {
                append("error", `A2A error: ${error}`);
                post("submitDone");
                return;
            }
            await this.handleResponse(response, folder, globalState, append, post, a2aBaseUrl, apiKey);
        }
        catch (e) {
            append("error", e instanceof Error ? e.message : String(e));
        }
        post("submitDone");
    }
    async handleResponse(res, folder, globalState, append, post, _a2aBaseUrl, _apiKey) {
        const status = res?.status;
        const rawState = status?.state ?? res?.state;
        const state = normalizeState(rawState);
        const statusMsg = status?.message ?? status;
        const messageText = getTextFromMessage(statusMsg && typeof statusMsg === "object" && "parts" in statusMsg
            ? statusMsg
            : undefined);
        if (state === "input_required") {
            append("message", messageText || "Agent needs your input.");
            globalState.update(PENDING_STATE_KEY, {
                taskId: String(res?.id ?? ""),
                contextId: String(res?.contextId ?? ""),
                workspaceUri: folder.uri.toString(),
            });
            post("setReplyMode", { active: true });
            return;
        }
        post("setReplyMode", { active: false });
        if (state === "completed") {
            const artifacts = extractRenameArtifacts(res);
            if (artifacts.length > 0) {
                try {
                    await applyArtifacts(folder, artifacts);
                    append("message", `Applied changes to ${artifacts.length} file(s).\n\n${messageText || ""}`);
                }
                catch (e) {
                    append("error", String(e));
                }
            }
            else {
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
function createSyncStatusBarItem() {
    const item = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
    item.show();
    return {
        item,
        update(status, message) {
            if (status === "ok") {
                item.text = "$(check) Refactor Agent: Sync OK";
                item.tooltip = "Sync service reachable";
                item.backgroundColor = undefined;
            }
            else if (status === "error") {
                item.text = "$(close) Refactor Agent: Sync error";
                item.tooltip = message ?? "Sync failed";
                item.backgroundColor = new vscode.ThemeColor("statusBarItem.errorBackground");
            }
            else {
                item.text = "$(circle-large-outline) Refactor Agent: Sync";
                item.tooltip = "Sync not checked yet";
                item.backgroundColor = undefined;
            }
        },
    };
}
function activate(extContext) {
    const syncStatus = createSyncStatusBarItem();
    extContext.subscriptions.push(syncStatus.item);
    const provider = new RefactorViewProvider(extContext, syncStatus);
    extContext.subscriptions.push(vscode.window.registerWebviewViewProvider("refactorAgent.refactorView", provider));
    extContext.subscriptions.push(vscode.commands.registerCommand("refactorAgent.focusView", () => {
        vscode.commands.executeCommand("refactorAgent.refactorView.focus");
    }));
    // Optional: check sync when view becomes visible (provider can call syncStatus.update after a quick check)
    // For now we only update on actual sync attempt during refactor.
}
function deactivate() { }
//# sourceMappingURL=extension.js.map