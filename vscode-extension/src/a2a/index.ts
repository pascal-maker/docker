import { parseStructuredError } from "../auth";
import { StructuredError } from "../types";

interface A2AResult {
  response: unknown;
  error?: string;
  structuredError?: StructuredError;
}

export async function sendA2AMessage(
  baseUrl: string,
  apiKey: string | undefined,
  payload: object
): Promise<A2AResult> {
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

export async function sendA2AResume(
  baseUrl: string,
  apiKey: string | undefined,
  taskId: string,
  contextId: string,
  userReplyText: string
): Promise<A2AResult> {
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
): Promise<A2AResult> {
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
    const text = await res.text();
    let data: {
      result?: Record<string, unknown>;
      error?: { message?: string };
    };
    try {
      data = JSON.parse(text) as {
        result?: Record<string, unknown>;
        error?: { message?: string };
      };
    } catch {
      data = {};
    }
    if (!res.ok) {
      const structured = parseStructuredError(res.status, text);
      return {
        response: data,
        error: structured.detail ?? structured.error ?? text,
        structuredError: structured,
      };
    }
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
