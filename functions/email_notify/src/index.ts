/**
 * Cloud Function: Firestore trigger to email admin on new pending user.
 * Triggered on document create in users collection when status is 'pending'.
 * Sends email via Resend to admin.
 */

import { cloudEvent } from "@google-cloud/functions-framework";

interface FirestoreValue {
  stringValue?: string;
  integerValue?: string;
  doubleValue?: number;
  booleanValue?: boolean;
  nullValue?: string;
  mapValue?: { fields?: Record<string, FirestoreValue> };
  arrayValue?: { values?: FirestoreValue[] };
}

interface DocumentEventData {
  value?: {
    name?: string;
    fields?: Record<string, FirestoreValue>;
  };
}

function parseFirestoreValue(
  val: FirestoreValue | undefined,
): string | number | boolean | null | Record<string, unknown> | unknown[] {
  if (!val) return null;
  if (val.nullValue != null) return null;
  if (val.stringValue != null) return val.stringValue;
  if (val.integerValue != null) return parseInt(val.integerValue, 10);
  if (val.doubleValue != null) return val.doubleValue;
  if (val.booleanValue != null) return val.booleanValue;
  if (val.mapValue?.fields)
    return Object.fromEntries(
      Object.entries(val.mapValue.fields).map(([k, v]) => [
        k,
        parseFirestoreValue(v),
      ]),
    );
  if (val.arrayValue?.values)
    return val.arrayValue.values.map((v) => parseFirestoreValue(v));
  return null;
}

interface ParsedUser {
  status?: string | null;
  github_login?: string | null;
  email?: string | null;
}

function parseFirestoreDocument(data: DocumentEventData): ParsedUser {
  const fields = data.value?.fields ?? {};
  const result: Record<string, unknown> = {};
  for (const [key, val] of Object.entries(fields)) {
    const parsed = parseFirestoreValue(val);
    if (
      typeof parsed === "string" ||
      typeof parsed === "number" ||
      typeof parsed === "boolean" ||
      parsed === null
    ) {
      result[key] = parsed;
    }
  }
  return {
    status: result["status"] != null ? String(result["status"]) : null,
    github_login:
      result["github_login"] != null ? String(result["github_login"]) : null,
    email: result["email"] != null ? String(result["email"]) : null,
  };
}

async function sendAdminNotification(
  adminEmail: string,
  apiKey: string,
  githubLogin: string,
  userEmail: string,
  fromEmail: string,
): Promise<void> {
  const payload = {
    from: fromEmail,
    to: [adminEmail],
    subject: `Refactor Agent: Access request from ${githubLogin}`,
    html: `<p>A new user has requested access to Refactor Agent.</p>
<p><strong>GitHub:</strong> ${githubLogin}</p>
<p><strong>Email:</strong> ${userEmail || "not provided"}</p>
<p>Approve via Firestore console or <code>scripts/auth/approve_user.py</code>.</p>`,
  };
  const res = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
      "User-Agent": "refactor-agent-email-notify/1.0",
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    // Log but don't throw - Firestore trigger shouldn't fail the event
    console.error("Resend API error:", res.status, await res.text());
  }
}

cloudEvent(
  "onUserCreated",
  async (cloudEvent: { data?: DocumentEventData }) => {
    const adminEmail = process.env["ADMIN_EMAIL"];
    const apiKey = process.env["RESEND_API_KEY"];
    const fromEmail =
      process.env["FROM_EMAIL"] ?? "Refactor Agent <noreply@refactorum.com>";

    if (!adminEmail || !apiKey) return;

    const rawData = (cloudEvent.data as DocumentEventData) ?? {};
    const docData = parseFirestoreDocument(rawData);

    if (docData.status !== "pending") return;

    const login = docData.github_login ?? "unknown";
    const userEmail = docData.email ?? "";

    await sendAdminNotification(
      adminEmail,
      apiKey,
      login,
      userEmail,
      fromEmail,
    );
  },
);
