export function getWebviewContent(nonce: string): string {
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'nonce-${nonce}'; style-src 'unsafe-inline'; img-src data:;">
  <style>
    html, body { height: 100%; min-height: 100vh; margin: 0; padding: 0; box-sizing: border-box; overflow: hidden; }
    body { font-family: var(--vscode-font-family); font-size: var(--vscode-font-size); color: var(--vscode-foreground); display: flex; flex-direction: column; padding: 8px; padding-bottom: 60px; }
    #messages { flex: 1; min-height: 0; overflow-y: auto; padding: 8px; font-size: 13px; line-height: 1.5; display: flex; flex-direction: column; }
    #messagesInner { flex: none; width: 100%; }
    .msg { margin: 6px 0; padding: 6px 8px; border-radius: 4px; }
    .msg.user { background: var(--vscode-input-background); margin-left: 16px; }
    .msg.agent { background: var(--vscode-editor-inactiveSelectionBackground); margin-right: 16px; }
    .msg.progress { color: var(--vscode-descriptionForeground); }
    .msg.error { color: var(--vscode-foreground); border-left: 3px solid var(--vscode-editorWarning-foreground); padding-left: 10px; }
    #messages pre, #messages code { font-family: var(--vscode-editor-font-family); font-size: 12px; }
    #messages code { background: var(--vscode-textCodeBlock-background); padding: 1px 4px; border-radius: 3px; }
    #messages pre { overflow-x: auto; padding: 8px; margin: 6px 0; }
    #messages pre code { padding: 0; background: transparent; }
    #messages a { color: var(--vscode-textLink-foreground); text-decoration: underline; }
    #messages a:hover { color: var(--vscode-textLink-activeForeground); }
    .conversation-row { margin-bottom: 8px; display: flex; align-items: center; gap: 8px; flex-shrink: 0; position: relative; }
    .conversation-dropdown-btn { flex: 1; display: flex; align-items: center; justify-content: space-between; padding: 6px 10px; font: inherit; background: var(--vscode-input-background); color: var(--vscode-input-foreground); border: 1px solid var(--vscode-input-border); border-radius: 4px; cursor: pointer; }
    .conversation-dropdown-btn:hover { background: var(--vscode-input-background); border-color: var(--vscode-focusBorder); }
    .conversation-dropdown-btn .chevron { margin-left: 4px; opacity: 0.7; }
    .conversation-dropdown-panel { display: none; position: absolute; top: 100%; left: 0; right: 0; margin-top: 4px; max-height: 240px; overflow-y: auto; background: var(--vscode-dropdown-background); border: 1px solid var(--vscode-dropdown-border); border-radius: 4px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); z-index: 100; }
    .conversation-dropdown-panel.open { display: block; }
    .conversation-item { padding: 8px 12px; cursor: pointer; font-size: 12px; display: flex; justify-content: space-between; align-items: center; gap: 8px; }
    .conversation-item:hover { background: var(--vscode-list-hoverBackground); }
    .conversation-item.active { background: var(--vscode-list-activeSelectionBackground); color: var(--vscode-list-activeSelectionForeground); }
    .conversation-item .item-main { flex: 1; min-width: 0; display: flex; justify-content: space-between; align-items: center; gap: 8px; }
    .conversation-item .time { font-size: 11px; opacity: 0.8; flex-shrink: 0; }
    .conversation-item .delete-btn { flex-shrink: 0; width: 20px; height: 20px; padding: 0; border: none; background: transparent; cursor: pointer; border-radius: 4px; display: flex; align-items: center; justify-content: center; opacity: 0.5; }
    .conversation-item .delete-btn:hover { opacity: 1; background: var(--vscode-toolbar-hoverBackground); }
    .conversation-new-btn { padding: 6px 10px; background: var(--vscode-button-background); color: var(--vscode-button-foreground); border: none; border-radius: 4px; cursor: pointer; font-size: 14px; line-height: 1; }
    .conversation-new-btn:hover { background: var(--vscode-button-hoverBackground); }
    .chatbox { position: fixed; bottom: 0; left: 0; right: 0; border: 1px solid var(--vscode-input-border); border-radius: 8px 8px 0 0; background: var(--vscode-input-background); padding: 10px 12px; display: flex; gap: 8px; align-items: flex-end; margin: 0 8px 8px 8px; }
    .chatbox:focus-within { border-color: var(--vscode-focusBorder); outline: 1px solid var(--vscode-focusBorder); outline-offset: -1px; }
    #chatInput { flex: 1; padding: 8px 10px; border: none; background: transparent; color: var(--vscode-input-foreground); font: inherit; resize: none; min-height: 20px; max-height: 120px; }
    #chatInput::placeholder { color: var(--vscode-input-placeholderForeground); }
    #chatInput:focus { outline: none; }
    #sendBtn { flex-shrink: 0; width: 32px; height: 32px; padding: 0; border: none; border-radius: 6px; background: var(--vscode-button-background); color: var(--vscode-button-foreground); cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 16px; line-height: 1; }
    #sendBtn:hover { background: var(--vscode-button-hoverBackground); }
    #sendBtn:disabled { opacity: 0.5; cursor: not-allowed; }
    .welcome-header { display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; margin-bottom: 12px; padding: 12px 0; flex-shrink: 0; }
    .welcome-header img { width: 48px; height: 48px; flex-shrink: 0; margin-bottom: 8px; }
    .welcome-header .splash { font-size: 12px; color: var(--vscode-descriptionForeground); line-height: 1.4; }
    #statusIndicator { display: flex; align-items: center; gap: 8px; margin-top: 12px; padding-top: 8px; flex-shrink: 0; }
    #statusIndicator .status-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
    #statusIndicator .status-dot.ok { background: var(--vscode-testing-iconPassed); }
    #statusIndicator .status-dot.syncing { background: var(--vscode-editorWarning-foreground); animation: pulse 1s ease-in-out infinite; }
    #statusIndicator .status-dot.error { background: var(--vscode-testing-iconFailed); }
    #statusIndicator .status-dot.pending { background: var(--vscode-textLink-foreground); }
    #statusIndicator .status-dot.unknown { background: var(--vscode-descriptionForeground); opacity: 0.6; }
    #statusIndicator .status-text { font-size: 11px; color: var(--vscode-descriptionForeground); opacity: 0.6; animation: shimmer 2s ease-in-out infinite; }
    @keyframes pulse { 0%, 100% { opacity: 0.5; } 50% { opacity: 1; } }
    @keyframes shimmer { 0%, 100% { opacity: 0.4; } 50% { opacity: 0.7; } }
    .welcome-messages { flex: 1; display: flex; flex-direction: column; min-height: 0; overflow: hidden; }
    .welcome-messages.empty { justify-content: center; }
    .welcome-messages.empty #messages { flex: 0; }
    .welcome-messages:not(.empty) .welcome-header { display: none; }
  </style>
</head>
<body>
  <div class="conversation-row">
    <button type="button" class="conversation-dropdown-btn" id="conversationDropdownBtn" aria-label="Past conversations" aria-haspopup="listbox" aria-expanded="false">
      <span id="conversationDropdownLabel">Past Conversations</span>
      <span class="chevron">&#9660;</span>
    </button>
    <button type="button" class="conversation-new-btn" id="conversationNewBtn" title="New chat" aria-label="New chat">+</button>
    <div class="conversation-dropdown-panel" id="conversationDropdownPanel" role="listbox">
    </div>
  </div>
  <div class="welcome-messages empty" id="welcomeMessages">
    <div class="welcome-header">
      <img src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%2360a5fa' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7'/%3E%3Cpath d='M18.5 2.5a2.12 2.12 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z'/%3E%3C/svg%3E" alt="Refactor Agent" />
      <div class="splash">Refactor Agent — restructure code with confidence.</div>
    </div>
    <div id="messages">
      <div id="messagesInner"></div>
      <div id="statusIndicator" aria-label="Status">
        <span class="status-dot unknown" id="statusDot"></span>
        <span class="status-text" id="statusText"></span>
      </div>
    </div>
  </div>
  <form id="chatForm" class="chatbox">
    <textarea id="chatInput" rows="1" placeholder="Refactor..." aria-label="Refactor request"></textarea>
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
    const messagesInner = document.getElementById('messagesInner');
    const statusDot = document.getElementById('statusDot');
    const statusText = document.getElementById('statusText');
    const conversationDropdownBtn = document.getElementById('conversationDropdownBtn');
    const conversationDropdownLabel = document.getElementById('conversationDropdownLabel');
    const conversationNewBtn = document.getElementById('conversationNewBtn');
    const conversationDropdownPanel = document.getElementById('conversationDropdownPanel');
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
        ln = (function linkify(s) {
          var out = '';
          var i = 0;
          while (i < s.length) {
            var lb = s.indexOf('[', i);
            if (lb < 0) { out += s.slice(i); break; }
            var rb = s.indexOf(']', lb + 1);
            if (rb < 0) { out += s.slice(i); break; }
            if (s.charAt(rb + 1) !== '(') { out += s.slice(i, rb + 1); i = rb + 1; continue; }
            var rp = s.indexOf(')', rb + 2);
            if (rp < 0) { out += s.slice(i); break; }
            var label = s.slice(lb + 1, rb);
            var url = s.slice(rb + 2, rp);
            if (url.indexOf('http://') === 0 || url.indexOf('https://') === 0) {
              out += s.slice(i, lb) + '<a href="' + url + '" target="_blank" rel="noopener noreferrer">' + label + '</a>';
              i = rp + 1;
            } else {
              out += s.slice(i, rb + 1);
              i = rb + 1;
            }
          }
          return out;
        })(ln);
        result.push(ln + '<br>');
        i++;
      }
      return result.join('\\n');
    }

    function updateEmptyState() {
      const wrapper = document.getElementById('welcomeMessages');
      if (wrapper && messagesInner) {
        wrapper.classList.toggle('empty', messagesInner.children.length === 0);
      }
    }

    var currentSyncState = 'unknown';
    var currentPhase = 'idle';
    function setStatusDot(syncState, phase) {
      if (syncState != null) currentSyncState = syncState;
      if (phase != null) currentPhase = phase;
      if (!statusDot) return;
      statusDot.className = 'status-dot ';
      var label = '';
      var text = '';
      if (currentPhase === 'syncing' || currentPhase === 'sending') {
        statusDot.classList.add('syncing');
        label = currentPhase === 'syncing' ? 'Syncing...' : 'Sending to agent...';
        text = currentPhase === 'syncing' ? 'syncing' : 'agenting';
      } else {
        var cls = currentSyncState === 'ok' ? 'ok' : currentSyncState === 'error' || currentSyncState === 'blocked' || currentSyncState === 'rate_limited' ? 'error' : currentSyncState === 'pending' ? 'pending' : 'unknown';
        statusDot.classList.add(cls);
        label = currentSyncState === 'ok' ? 'Synced' : currentSyncState === 'error' ? 'Connection error' : currentSyncState === 'blocked' ? 'Access restricted' : currentSyncState === 'rate_limited' ? 'Rate limited' : currentSyncState === 'pending' ? 'Access pending' : 'Not checked';
        text = '';
      }
      statusDot.title = label;
      if (statusText) {
        statusText.textContent = text;
        statusText.style.animation = (currentPhase === 'syncing' || currentPhase === 'sending') ? 'shimmer 2s ease-in-out infinite' : 'none';
      }
    }

    function appendMessage(role, kind, text, useMarkdown) {
      if (!messagesInner) return;
      const el = document.createElement('div');
      el.className = 'msg ' + (role || 'agent') + (kind ? ' ' + kind : '');
      const safeText = (text != null && typeof text !== 'string') ? String(text) : (text || '');
      if (useMarkdown && (role === 'agent' || role === 'user')) {
        el.innerHTML = renderMarkdown(safeText);
      } else {
        el.textContent = safeText;
      }
      messagesInner.appendChild(el);
      if (messages) messages.scrollTop = messages.scrollHeight;
      updateEmptyState();
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

    function formatRelativeTime(ts) {
      if (ts == null || typeof ts !== 'number') return '';
      const sec = Math.floor((Date.now() - ts) / 1000);
      if (sec < 60) return sec + 's';
      if (sec < 3600) return Math.floor(sec / 60) + 'm';
      if (sec < 86400) return Math.floor(sec / 3600) + 'h';
      return Math.floor(sec / 86400) + 'd';
    }

    function closeDropdown() {
      if (conversationDropdownPanel) conversationDropdownPanel.classList.remove('open');
      if (conversationDropdownBtn) conversationDropdownBtn.setAttribute('aria-expanded', 'false');
    }

    conversationDropdownBtn && conversationDropdownBtn.addEventListener('click', () => {
      const open = conversationDropdownPanel && conversationDropdownPanel.classList.toggle('open');
      conversationDropdownBtn && conversationDropdownBtn.setAttribute('aria-expanded', String(open));
    });

    conversationNewBtn && conversationNewBtn.addEventListener('click', () => {
      closeDropdown();
      vscode.postMessage({ type: 'newChat' });
    });

    document.addEventListener('click', (e) => {
      if (conversationDropdownPanel && conversationDropdownPanel.classList.contains('open') &&
          conversationDropdownBtn && conversationNewBtn &&
          !conversationDropdownBtn.contains(e.target) && !conversationNewBtn.contains(e.target) &&
          !conversationDropdownPanel.contains(e.target)) {
        closeDropdown();
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
        if (conversationDropdownLabel) {
          const current = list.find(function(c) { return c && c.id === currentId; });
          conversationDropdownLabel.textContent = current ? (current.title || 'Chat') : 'Past Conversations';
        }
        if (conversationDropdownPanel) {
          conversationDropdownPanel.innerHTML = '';
          if (list.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'conversation-item';
            empty.style.cursor = 'default';
            empty.style.opacity = '0.7';
            empty.textContent = 'No conversations yet';
            conversationDropdownPanel.appendChild(empty);
          } else {
            list.forEach(function(c) {
              if (!c || typeof c.id !== 'string') return;
              const item = document.createElement('div');
              item.className = 'conversation-item' + (c.id === currentId ? ' active' : '');
              item.setAttribute('role', 'option');
              item.setAttribute('data-id', c.id);
              const main = document.createElement('span');
              main.className = 'item-main';
              const title = document.createElement('span');
              title.textContent = (c.title != null ? String(c.title) : 'Chat') || 'Chat';
              title.style.overflow = 'hidden';
              title.style.textOverflow = 'ellipsis';
              title.style.whiteSpace = 'nowrap';
              const time = document.createElement('span');
              time.className = 'time';
              time.textContent = formatRelativeTime(c.createdAt);
              main.appendChild(title);
              main.appendChild(time);
              const delBtn = document.createElement('button');
              delBtn.className = 'delete-btn';
              delBtn.type = 'button';
              delBtn.title = 'Delete';
              delBtn.setAttribute('aria-label', 'Delete conversation');
              delBtn.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>';
              delBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                vscode.postMessage({ type: 'deleteConversation', id: c.id });
              });
              item.appendChild(main);
              item.appendChild(delBtn);
              item.addEventListener('click', function(e) {
                if (e.target !== delBtn && !delBtn.contains(e.target)) {
                  vscode.postMessage({ type: 'selectConversation', id: c.id });
                  closeDropdown();
                }
              });
              conversationDropdownPanel.appendChild(item);
            });
          }
        }
        if (messagesInner) messagesInner.innerHTML = '';
        msgs.forEach(function(m) {
          try {
            appendMessage(m && m.role, m && m.kind, m && m.text, true);
          } catch (err) {
            logErr('restore appendMessage error', err);
            appendMessage('agent', 'error', String(m && m.text || 'Invalid message'), false);
          }
        });
        if (messages) messages.scrollTop = messages.scrollHeight;
        updateEmptyState();
      } else if (msg.type === 'append') {
        try {
          appendMessage(msg.role || 'agent', msg.kind, msg.text, true);
        } catch (err) {
          logErr('append error', err, 'msg.text type=', typeof msg.text);
          if (messagesInner) {
            const fallback = document.createElement('div');
            fallback.className = 'msg agent error';
            fallback.textContent = typeof msg.text === 'string' ? msg.text : 'Message could not be displayed';
            messagesInner.appendChild(fallback);
            updateEmptyState();
          }
        }
      } else if (msg.type === 'submitDone') {
        if (sendBtn) sendBtn.disabled = false;
      } else if (msg.type === 'syncStatus') {
        setStatusDot(msg.status, null);
      } else if (msg.type === 'setStatus') {
        setStatusDot(null, msg.phase);
      }
    });

    log('posting ready');
    vscode.postMessage({ type: 'ready' });
    })();
  </script>
</body>
</html>`;
}

// TODO: Is this safe? Should nonce be extracted to const file or .env var? Idk much about security.
export function getNonce(): string {
  let out = "";
  const pool = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
  for (let i = 0; i < 32; i++) {
    out += pool.charAt(Math.floor(Math.random() * pool.length));
  }
  return out;
}
