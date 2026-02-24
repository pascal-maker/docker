export interface PendingReply {
  taskId: string;
  contextId: string;
  workspaceUri: string;
}

interface ChatMessage {
  role: "user" | "agent";
  kind?: string;
  text: string;
}

export interface Conversation {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt?: number;
}

export interface SyncStatusUpdater {
  update(status: SyncStatus, message?: string): void;
}

export interface StructuredError {
  statusCode: number;
  error?: string;
  detail?: string;
  raw?: string;
}

export type SyncStatus =
  | "ok"
  | "error"
  | "pending"
  | "blocked"
  | "rate_limited"
  | "unknown";

export type Engine = "python" | "typescript";
