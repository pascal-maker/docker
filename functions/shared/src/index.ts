/** Shared package for Cloud Functions: schemas, HTTP helpers, Firestore. */

export {
  GitHubEmailSchema,
  GitHubInstallationRefSchema,
  GitHubInstallationSchema,
  GitHubInstallationsResponseSchema,
  GitHubRepositoriesResponseSchema,
  GitHubTokenResponseSchema,
  GitHubUserSchema,
  GitHubWebhookPayloadSchema,
  RepoAccessSchema,
  RepoRefSchema,
} from "./github.js";
export type {
  GitHubEmail,
  GitHubInstallation,
  GitHubInstallationRef,
  GitHubInstallationsResponse,
  GitHubRepositoriesResponse,
  GitHubTokenResponse,
  GitHubUser,
  GitHubWebhookPayload,
  RepoAccess,
  RepoRef,
} from "./github.js";

export {
  collectReposAndInstallationIds,
  exchangeCode,
  fetchGitHubUser,
  fetchInstallationRepos,
  fetchInstallations,
  fetchPrimaryEmail,
} from "./github_api.js";

export { httpHandler } from "./http.js";
export type { HttpHandler, HttpHandlerFn, HttpResponse } from "./http.js";

export {
  getInstallationUserIds,
  updateUserRepos,
  writeUserToFirestore,
} from "./firestore.js";
