/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_GITHUB_OAUTH_CLIENT_ID?: string;
  readonly VITE_GITHUB_APP_CLIENT_ID?: string;
  readonly VITE_AUTH_CALLBACK_URL?: string;
  readonly VITE_SENTRY_DSN?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
