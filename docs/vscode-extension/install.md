# Installing the Refactor Agent extension

## From the repo (development)

1. Build the extension:
   ```bash
   cd vscode-extension
   pnpm install
   pnpm run compile
   ```

2. Run from source (Extension Development Host):
   - Open this repo in VS Code or Cursor.
   - Press **F5** (or Run and Debug → "Run Extension"). A new window opens with the extension loaded.
   - No need to restart Docker or the A2A server; the extension runs in the dev host.

3. Or install the built extension into your editor so it’s available in every window:
   - **VS Code:** From `vscode-extension` (after `pnpm run compile`): `code --install-extension .`
   - **Cursor:** Use the same pattern if your Cursor build supports a CLI, or use **Install from VSIX** (see below) after packaging.

## From a VSIX

Package and install:

```bash
cd vscode-extension
pnpm run compile
pnpm dlx vsce package
```

Then install the generated `.vsix` via **Extensions** → **…** → **Install from VSIX…** (or `code --install-extension refactor-agent-0.1.0.vsix`).

## Having the extension available by default in this repo

Ways to make the extension show up or install easily when you open this repo:

- **Workspace recommendations**  
  Add the extension to `.vscode/extensions.json` under `recommendations`. When you (or others) open the repo, the editor can prompt to install it. The extension must be installable by ID (published to the [Marketplace](https://marketplace.visualstudio.com/) for VS Code or [Open VSX](https://open-vsx.org/) for Cursor). After publishing, add e.g. `"refactor-agent.refactor-agent"` to `recommendations`.

- **Install from path once**  
  After building, run `code --install-extension .` from `vscode-extension`. The extension is then installed for that editor and available in every window, including when you open this repo. No Docker restart needed for extension-only changes; run `pnpm run compile` and **Developer: Reload Window** to pick up code changes.

- **Symlink into the extensions directory**  
  Symlink the built `vscode-extension` folder into your editor’s extensions directory (e.g. `~/.vscode/extensions/` or Cursor’s equivalent) with the usual folder name (e.g. `refactor-agent.refactor-agent-0.1.0`). The extension is then always “installed” and updates when you change and recompile the repo.

After any code change, run `pnpm run compile` in `vscode-extension` and **Developer: Reload Window**; you do not need to restart the A2A server or Docker.
