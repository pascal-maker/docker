# Debugging the Refactor Agent extension

## When the panel is blank or messages don't show

1. **Open the Extension Development Host**  
   Run the extension (F5 or "Run and Debug" > "Run Extension"). Open a workspace (e.g. `playground/typescript`).

2. **Open the Refactor Agent view**  
   Click the Refactor Agent icon in the activity bar so the webview panel is visible.

3. **Open Webview Developer Tools**  
   - Press `Cmd+Shift+P` (Mac) or `Ctrl+Shift+P` (Windows/Linux).
   - Run: **"Refactor Agent: Open Webview Developer Tools"**  
     (or search for "Open Webview Developer Tools" and pick the one that targets webviews.)
   - A DevTools window opens. Focus the **Console** tab.

4. **Check the console**
   - You should see `[Refactor Agent] Webview script loaded. messages= true chatForm= true` when the webview loads.
   - When you send a message, you should see `[Refactor Agent] message received submit` and then `append` messages.
   - Any JavaScript error (e.g. "Cannot read property X of null") will appear in red. That points to the real bug.

5. **If "Open Webview Developer Tools" doesn't appear**
   - Use **"Developer: Toggle Developer Tools"** to open the main window DevTools. The webview may be in an iframe; use the frame dropdown at the top of the Console to select the webview frame, then check for `[Refactor Agent]` logs and errors there.

## What the logs mean

- **Webview script loaded** – The script ran. If the panel is still blank, the DOM might be hidden (e.g. CSS) or a later line threw.
- **message received restore** – The extension sent conversation state. Check that `convs` and `msgs` counts look right.
- **message received append** – The extension sent one message to show in the chat. If you see "append" but no new bubble, the error may be in `appendMessage` or `renderMarkdown` (see red error in console).
- **restore appendMessage error** / **append error** – One message failed to render; the code will show a fallback. The logged error object and stack trace tell you why.

## Fixing after you see the error

- **"messages is null"** – The `#messages` element wasn't found when the script ran (e.g. wrong ID or HTML structure). Check `getWebviewContent()` in `src/extension.ts`.
- **"escapeHtml is not a function"** or **"renderMarkdown is not a function"** – The script may be truncated or broken by a syntax error in the template literal (e.g. unescaped backtick).
- **"Cannot read property 'appendChild' of null"** – Same as above: the element reference is null. Ensure the script runs after the DOM is ready (it's at the end of `<body>` so it should be).

After changing the extension code, run "Developer: Reload Window" in the Extension Development Host so the webview is recreated with the new script.
