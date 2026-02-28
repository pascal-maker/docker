import { init as initSentry } from "@sentry/node";
import * as vscode from "vscode";
import { RefactorAgentAuthProvider } from "./auth/RefactorAgentAuthProvider";
import { createSyncStatusBarItem } from "./statusBar";
import { RefactorViewProvider } from "./RefactorViewProvider";

export function activate(extContext: vscode.ExtensionContext): void {
  const dsn =
    vscode.workspace
      .getConfiguration("refactorAgent")
      .get<string>("sentryDsn") ??
    process.env.SENTRY_DSN ??
    "";
  if (dsn) {
    initSentry({
      dsn,
      tracesSampleRate: 0,
    });
  }

  const authProvider = new RefactorAgentAuthProvider(extContext);
  const uriHandler = {
    handleUri: (uri: vscode.Uri) => {
      authProvider.handleCallback(uri);
    },
  };
  extContext.subscriptions.push(vscode.window.registerUriHandler(uriHandler));

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
