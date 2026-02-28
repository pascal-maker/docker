/**
 * Cloud Function: GitHub App OAuth callback for site access requests.
 * Exchanges authorization code for user-to-server token, fetches user and
 * installations from GitHub, writes to Firestore with status='pending' and
 * allowed_repos, redirects to site or vscode:// for extension.
 */

import type { Request, Response } from "express";
import { http } from "@google-cloud/functions-framework";
import {
  collectReposAndInstallationIds,
  exchangeCode,
  fetchGitHubUser,
  fetchPrimaryEmail,
  fetchInstallations,
  httpHandler,
  type HttpResponse,
  writeUserToFirestore,
} from "@refactor-agent/functions-shared";

function redirectTo(url: string, status = 302): HttpResponse {
  return { body: "", status, headers: { Location: url } };
}

function resolveRedirectUrl(
  baseUrl: string,
  state: string,
  token: string,
): string {
  const base = baseUrl.replace(/\/$/, "");
  const stateLower = state.toLowerCase();
  if (state.includes("return:vscode") || stateLower.includes("vscode")) {
    return `${base}/auth/success?token=${encodeURIComponent(token)}`;
  }
  return `${base}/success`;
}

const handler: (req: Request, res: Response) => void | Promise<void> =
  httpHandler(async (req, _res): Promise<HttpResponse> => {
    const code = req.query["code"];
    const state = (req.query["state"] as string) ?? "";
    const baseUrl = process.env["SITE_URL"] ?? "http://localhost:5173";
    const errorUrl = baseUrl.replace(/\/$/, "") + "/error";

    if (typeof code !== "string" || !code) {
      return redirectTo(errorUrl);
    }

    const clientId = process.env["GITHUB_APP_CLIENT_ID"];
    const clientSecret = process.env["GITHUB_APP_CLIENT_SECRET"];
    const redirectUri = process.env["GITHUB_OAUTH_REDIRECT_URI"];
    const project =
      process.env["GOOGLE_CLOUD_PROJECT"] ?? process.env["GCP_PROJECT"];

    if (!clientId || !clientSecret || !redirectUri || !project) {
      return redirectTo(errorUrl);
    }

    const tokenResponse = await exchangeCode(
      code,
      clientId,
      clientSecret,
      redirectUri,
    );
    if (!tokenResponse) {
      return redirectTo(errorUrl);
    }

    const token = tokenResponse.access_token;
    const userData = await fetchGitHubUser(token);
    if (!userData) {
      return redirectTo(errorUrl);
    }

    const userId = String(userData.id);
    const login = userData.login;
    const email = userData.email ?? (await fetchPrimaryEmail(token));

    const installations = await fetchInstallations(token);
    const { allowedRepos, installationIds } =
      await collectReposAndInstallationIds(token, installations);

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
      return redirectTo(errorUrl);
    }

    const redirectUrl = resolveRedirectUrl(baseUrl, state, token);
    return redirectTo(redirectUrl);
  });

http("authCallback", handler);

export { handler as authCallback };
