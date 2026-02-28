/** GitHub API and webhook models (Zod schemas). */

import { z } from "zod";

/** Repository reference from webhook payload or GitHub API. */
export const RepoRefSchema = z.object({
  full_name: z.string(),
  id: z.number(),
});
export type RepoRef = z.infer<typeof RepoRefSchema>;

/** Installation reference from webhook payload. */
export const GitHubInstallationRefSchema = z.object({
  id: z.number(),
});
export type GitHubInstallationRef = z.infer<typeof GitHubInstallationRefSchema>;

/** GitHub App installation_repositories webhook payload. */
export const GitHubWebhookPayloadSchema = z.object({
  action: z.string(),
  installation: GitHubInstallationRefSchema,
  repositories_added: z.array(RepoRefSchema).default([]),
  repositories_removed: z.array(RepoRefSchema).default([]),
});
export type GitHubWebhookPayload = z.infer<typeof GitHubWebhookPayloadSchema>;

/** GitHub OAuth token exchange response. */
export const GitHubTokenResponseSchema = z.object({
  access_token: z.string(),
  token_type: z.string().default("bearer"),
  scope: z.string().optional(),
  expires_in: z.number().optional(),
});
export type GitHubTokenResponse = z.infer<typeof GitHubTokenResponseSchema>;

/** GitHub user from /user API. */
export const GitHubUserSchema = z.object({
  id: z.number(),
  login: z.string(),
  email: z.string().optional(),
});
export type GitHubUser = z.infer<typeof GitHubUserSchema>;

/** Repository access from GitHub App installation. */
export const RepoAccessSchema = z.object({
  full_name: z.string(),
  id: z.number(),
});
export type RepoAccess = z.infer<typeof RepoAccessSchema>;

/** GitHub App installation (minimal for filtering). */
export const GitHubInstallationSchema = z.object({
  id: z.number(),
  app_id: z.number().optional(),
});
export type GitHubInstallation = z.infer<typeof GitHubInstallationSchema>;

/** GitHub /user/emails item. */
export const GitHubEmailSchema = z.object({
  email: z.string(),
  primary: z.boolean().optional(),
  verified: z.boolean().optional(),
});
export type GitHubEmail = z.infer<typeof GitHubEmailSchema>;

/** GitHub /user/installations response. */
export const GitHubInstallationsResponseSchema = z.object({
  installations: z.array(GitHubInstallationSchema).default([]),
});
export type GitHubInstallationsResponse = z.infer<
  typeof GitHubInstallationsResponseSchema
>;

/** GitHub /user/installations/{id}/repositories response. */
export const GitHubRepositoriesResponseSchema = z.object({
  repositories: z.array(RepoAccessSchema).default([]),
});
export type GitHubRepositoriesResponse = z.infer<
  typeof GitHubRepositoriesResponseSchema
>;
