/**
 * Cloud Function: Register user from device flow token.
 * Accepts POST with Authorization: Bearer <token>. Verifies token is from our
 * GitHub App (app_id check), fetches user and installations, writes to Firestore.
 * Used by VS Code extension when device flow is used instead of browser redirect.
 */

import type { Request, Response } from "express";
import { http } from "@google-cloud/functions-framework";
import {
  collectReposAndInstallationIds,
  fetchGitHubUser,
  fetchInstallations,
  fetchPrimaryEmail,
  httpHandler,
  type HttpResponse,
  writeUserToFirestore,
} from "@refactor-agent/functions-shared";
import type { GitHubInstallation } from "@refactor-agent/functions-shared";

function jsonResponse(body: string, status: number): HttpResponse {
  return { body, status, headers: { "Content-Type": "application/json" } };
}

function validateRegisterRequest(
  req: Request,
): { ok: true; token: string } | { ok: false; body: string; status: number } {
  if (req.method !== "POST") {
    return {
      ok: false,
      body: JSON.stringify({ error: "Method not allowed" }),
      status: 405,
    };
  }

  const auth = req.headers["authorization"] ?? "";
  if (!auth.startsWith("Bearer ")) {
    return {
      ok: false,
      body: JSON.stringify({
        error: "Missing or invalid Authorization header",
      }),
      status: 401,
    };
  }

  const token = auth.slice(7).trim();
  if (!token) {
    return {
      ok: false,
      body: JSON.stringify({ error: "Empty token" }),
      status: 401,
    };
  }

  return { ok: true, token };
}

function filterOurInstallations(
  installations: GitHubInstallation[],
  appIdStr: string,
):
  | { ok: true; installations: GitHubInstallation[] }
  | { ok: false; body: string; status: number } {
  const trimmed = appIdStr.trim();
  if (!trimmed) {
    return {
      ok: false,
      body: JSON.stringify({ error: "Server misconfiguration" }),
      status: 503,
    };
  }

  const expectedAppId = parseInt(trimmed, 10);
  if (Number.isNaN(expectedAppId)) {
    return {
      ok: false,
      body: JSON.stringify({ error: "Server misconfiguration" }),
      status: 503,
    };
  }

  const ourInstallations = installations.filter(
    (i) => i.app_id === expectedAppId,
  );
  if (ourInstallations.length === 0) {
    return {
      ok: false,
      body: JSON.stringify({ error: "Token not from Refactor Agent app" }),
      status: 403,
    };
  }

  return { ok: true, installations: ourInstallations };
}

const handler: (req: Request, res: Response) => void | Promise<void> =
  httpHandler(async (req, _res): Promise<HttpResponse> => {
    const validated = validateRegisterRequest(req);
    if (!validated.ok) {
      return jsonResponse(validated.body, validated.status);
    }

    const { token } = validated;
    const userData = await fetchGitHubUser(token);
    if (!userData) {
      return jsonResponse(JSON.stringify({ error: "Invalid token" }), 401);
    }

    const installations = await fetchInstallations(token);
    const appIdStr = process.env["GITHUB_APP_ID"] ?? "";
    const filtered = filterOurInstallations(installations, appIdStr);

    if (!filtered.ok) {
      return jsonResponse(filtered.body, filtered.status);
    }

    const project =
      process.env["GOOGLE_CLOUD_PROJECT"] ?? process.env["GCP_PROJECT"];
    if (!project) {
      return jsonResponse(
        JSON.stringify({ error: "Server misconfiguration" }),
        503,
      );
    }

    const userId = String(userData.id);
    const login = userData.login;
    const email = userData.email ?? (await fetchPrimaryEmail(token));

    const { allowedRepos, installationIds } =
      await collectReposAndInstallationIds(token, filtered.installations);

    try {
      await writeUserToFirestore(
        project,
        userId,
        login,
        email ?? null,
        allowedRepos,
        installationIds,
      );
    } catch {
      return jsonResponse(
        JSON.stringify({ error: "Failed to register user" }),
        500,
      );
    }

    return jsonResponse(JSON.stringify({ ok: true }), 200);
  });

http("authRegisterDevice", handler);

export { handler as authRegisterDevice };
