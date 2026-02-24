import * as Sentry from "@sentry/react";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";

Sentry.init({
  dsn: import.meta.env.VITE_SENTRY_DSN ?? "",
  tracesSampleRate: 0,
  replaysSessionSampleRate: 0,
});

const rootEl = document.getElementById("root");
if (rootEl == null) throw new Error("root element missing");
createRoot(rootEl).render(
  <StrictMode>
    <App />
  </StrictMode>
);
