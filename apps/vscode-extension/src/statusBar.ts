import { SyncStatus, SyncStatusUpdater } from "./types";
import vscode from "vscode";

export function createSyncStatusBarItem(): SyncStatusUpdater & {
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
      } else if (status === "pending") {
        item.text = "$(info) Refactor Agent: Access pending";
        item.tooltip = message ?? "Request access to get started";
        item.backgroundColor = new vscode.ThemeColor(
          "statusBarItem.prominentBackground"
        );
      } else if (status === "blocked") {
        item.text = "$(warning) Refactor Agent: Access restricted";
        item.tooltip = message ?? "Your access has been restricted";
        item.backgroundColor = new vscode.ThemeColor(
          "statusBarItem.warningBackground"
        );
      } else if (status === "rate_limited") {
        item.text = "$(watch) Refactor Agent: Rate limited";
        item.tooltip = message ?? "Please try again in a few minutes";
        item.backgroundColor = new vscode.ThemeColor(
          "statusBarItem.warningBackground"
        );
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
