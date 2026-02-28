/** GitHub API fetch helpers. All responses validated with Zod. */

import {
  GitHubInstallationsResponseSchema,
  GitHubRepositoriesResponseSchema,
  GitHubTokenResponseSchema,
  GitHubUserSchema,
  type GitHubEmail,
  type GitHubInstallation,
  type RepoAccess,
} from "./github.js";

const GITHUB_API_HEADERS = {
  Accept: "application/vnd.github+json",
  "X-GitHub-Api-Version": "2022-11-28",
};

/** Exchange GitHub App OAuth code for access token. */
export async function exchangeCode(
  code: string,
  clientId: string,
  clientSecret: string,
  redirectUri: string,
): Promise<{ access_token: string } | null> {
  const body = new URLSearchParams({
    client_id: clientId,
    client_secret: clientSecret,
    code: code.trim(),
    redirect_uri: redirectUri,
  });

  const res = await fetch("https://github.com/login/oauth/access_token", {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: body.toString(),
    signal: AbortSignal.timeout(10_000),
  });

  if (!res.ok) return null;
  const raw = (await res.json()) as unknown;
  const parsed = GitHubTokenResponseSchema.safeParse(raw);
  return parsed.success ? parsed.data : null;
}

/** Fetch GitHub user via /user API. */
export async function fetchGitHubUser(
  token: string,
): Promise<{ id: number; login: string; email?: string } | null> {
  const res = await fetch("https://api.github.com/user", {
    headers: {
      Authorization: `Bearer ${token}`,
      ...GITHUB_API_HEADERS,
    },
    signal: AbortSignal.timeout(10_000),
  });

  if (!res.ok) return null;
  const raw = (await res.json()) as unknown;
  const parsed = GitHubUserSchema.safeParse(raw);
  if (!parsed.success) return null;
  const { id, login, email } = parsed.data;
  return { id, login, ...(email !== undefined && { email }) };
}

/** Fetch primary email from /user/emails. */
export async function fetchPrimaryEmail(token: string): Promise<string | null> {
  const res = await fetch("https://api.github.com/user/emails", {
    headers: {
      Authorization: `Bearer ${token}`,
      ...GITHUB_API_HEADERS,
    },
    signal: AbortSignal.timeout(10_000),
  });

  if (!res.ok) return null;
  const raw = (await res.json()) as unknown;
  if (!Array.isArray(raw)) return null;

  const emails = raw as unknown[];
  for (const e of emails) {
    if (
      typeof e === "object" &&
      e !== null &&
      "primary" in e &&
      "verified" in e &&
      (e as GitHubEmail).primary &&
      (e as GitHubEmail).verified
    ) {
      return (e as GitHubEmail).email ?? null;
    }
  }
  for (const e of emails) {
    if (
      typeof e === "object" &&
      e !== null &&
      "verified" in e &&
      (e as GitHubEmail).verified
    ) {
      return (e as GitHubEmail).email ?? null;
    }
  }
  return null;
}

/** Fetch user installations. */
export async function fetchInstallations(
  token: string,
): Promise<GitHubInstallation[]> {
  const res = await fetch(
    "https://api.github.com/user/installations?per_page=100",
    {
      headers: {
        Authorization: `Bearer ${token}`,
        ...GITHUB_API_HEADERS,
      },
      signal: AbortSignal.timeout(10_000),
    },
  );

  if (!res.ok) return [];
  const raw = (await res.json()) as unknown;
  const parsed = GitHubInstallationsResponseSchema.safeParse(raw);
  return parsed.success ? parsed.data.installations : [];
}

/** Fetch repos for an installation. */
export async function fetchInstallationRepos(
  token: string,
  installationId: number,
): Promise<RepoAccess[]> {
  const res = await fetch(
    `https://api.github.com/user/installations/${installationId}/repositories?per_page=100`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
        ...GITHUB_API_HEADERS,
      },
      signal: AbortSignal.timeout(10_000),
    },
  );

  if (!res.ok) return [];
  const raw = (await res.json()) as unknown;
  const parsed = GitHubRepositoriesResponseSchema.safeParse(raw);
  return parsed.success ? parsed.data.repositories : [];
}

/** Collect allowed_repos and installation_ids from installations. */
export async function collectReposAndInstallationIds(
  token: string,
  installations: GitHubInstallation[],
): Promise<{ allowedRepos: RepoAccess[]; installationIds: number[] }> {
  const allowedRepos: RepoAccess[] = [];
  const seen = new Set<string>();
  const installationIds: number[] = [];

  for (const inst of installations) {
    installationIds.push(inst.id);
    const repos = await fetchInstallationRepos(token, inst.id);
    for (const r of repos) {
      const key = `${r.full_name}:${r.id}`;
      if (!seen.has(key)) {
        seen.add(key);
        allowedRepos.push(r);
      }
    }
  }

  return { allowedRepos, installationIds };
}
