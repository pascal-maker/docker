/**
 * Cloud Function: GitHub App webhook handler for installation_repositories.
 * Updates allowed_repos in Firestore when users add or remove repos from the
 * GitHub App installation.
 */

import { createHmac, timingSafeEqual } from "node:crypto";
import type { Request, Response } from "express";
import { http } from "@google-cloud/functions-framework";
import type { GitHubWebhookPayload } from "@refactor-agent/functions-shared";
import {
  getInstallationUserIds,
  GitHubWebhookPayloadSchema,
  httpHandler,
  type HttpResponse,
  updateUserRepos,
} from "@refactor-agent/functions-shared";

function verifySignature(
  payloadBody: Buffer,
  signature: string | undefined,
  secret: string,
): boolean {
  if (!signature || !signature.startsWith("sha256=")) {
    return false;
  }
  const sigHex = signature.slice(7);
  const expected = createHmac("sha256", secret)
    .update(payloadBody)
    .digest("hex");
  if (sigHex.length !== expected.length) {
    return false;
  }
  return timingSafeEqual(
    Buffer.from(sigHex, "hex"),
    Buffer.from(expected, "hex"),
  );
}

type ValidatedResult =
  | { ok: true; project: string; payload: GitHubWebhookPayload }
  | { ok: false; body: string; status: number };

function validateRequest(req: {
  method?: string;
  rawBody?: Buffer;
  get: (name: string) => string | undefined;
}): ValidatedResult {
  if (req.method !== "POST") {
    return { ok: false, body: "Method not allowed", status: 405 };
  }

  const secret = process.env["GITHUB_WEBHOOK_SECRET"];
  const project =
    process.env["GOOGLE_CLOUD_PROJECT"] ?? process.env["GCP_PROJECT"];
  if (!secret || !project) {
    return { ok: false, body: "Webhook not configured", status: 503 };
  }

  const rawBody = req.rawBody;
  if (!rawBody || rawBody.length === 0) {
    return { ok: false, body: "Invalid payload", status: 400 };
  }

  const signature =
    req.get("X-Hub-Signature-256") ?? req.get("x-hub-signature-256");
  if (!verifySignature(rawBody, signature, secret)) {
    return { ok: false, body: "Invalid signature", status: 401 };
  }

  let raw: unknown;
  try {
    raw = JSON.parse(rawBody.toString("utf8")) as unknown;
  } catch {
    return { ok: false, body: "Invalid JSON", status: 400 };
  }

  const parseResult = GitHubWebhookPayloadSchema.safeParse(raw);
  if (!parseResult.success) {
    return { ok: false, body: "Invalid payload", status: 400 };
  }

  const payload = parseResult.data;
  return { ok: true, project, payload };
}

async function processInstallationRepos(
  project: string,
  installationId: number,
  action: string,
  reposAdded: GitHubWebhookPayload["repositories_added"],
  reposRemoved: GitHubWebhookPayload["repositories_removed"],
): Promise<void> {
  const userIds = await getInstallationUserIds(project, installationId);
  const toAdd = action === "added" ? reposAdded : [];
  const toRemove = action === "removed" ? reposRemoved : [];

  for (const userId of userIds) {
    await updateUserRepos(project, userId, toAdd, toRemove);
  }
}

const handler: (req: Request, res: Response) => void | Promise<void> =
  httpHandler(async (req, _res): Promise<HttpResponse> => {
    const validated = validateRequest(req);

    if (!validated.ok) {
      return { body: validated.body, status: validated.status };
    }

    const { project, payload } = validated;
    if (payload.action !== "added" && payload.action !== "removed") {
      return { body: "OK", status: 200 };
    }

    await processInstallationRepos(
      project,
      payload.installation.id,
      payload.action,
      payload.repositories_added,
      payload.repositories_removed,
    );

    return { body: "OK", status: 200 };
  });

http("githubWebhook", handler);

export { handler as githubWebhook };
