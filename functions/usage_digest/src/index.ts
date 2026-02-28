/**
 * Cloud Function: Daily usage digest email.
 * HTTP-triggered by Cloud Scheduler. Queries Firestore (new users) and Cloud
 * Monitoring (auth/email function invocations), sends digest via Resend.
 */

import { Firestore } from "@google-cloud/firestore";
import { http } from "@google-cloud/functions-framework";
import { MetricServiceClient } from "@google-cloud/monitoring";
import {
  httpHandler,
  type HttpResponse,
} from "@refactor-agent/functions-shared";

async function countNewUsers(projectId: string): Promise<number> {
  const db = new Firestore({ projectId });
  const cutoff = new Date(Date.now() - 24 * 60 * 60 * 1000);
  const snapshot = await db
    .collection("users")
    .where("created_at", ">=", cutoff)
    .count()
    .get();
  return snapshot.data().count;
}

async function getRequestCount(
  projectId: string,
  client: MetricServiceClient,
  serviceName: string,
  startTime: Date,
  endTime: Date,
): Promise<number> {
  const filter = `metric.type="run.googleapis.com/request_count" AND resource.type="cloud_run_revision" AND resource.labels.service_name="${serviceName}"`;
  const [response] = await client.listTimeSeries({
    name: `projects/${projectId}`,
    filter,
    interval: {
      startTime: { seconds: Math.floor(startTime.getTime() / 1000) },
      endTime: { seconds: Math.floor(endTime.getTime() / 1000) },
    },
    aggregation: {
      alignmentPeriod: { seconds: 86400 },
      perSeriesAligner: "ALIGN_SUM",
    },
    view: "FULL",
  });

  const timeSeries = Array.isArray(response) ? response : [];
  let total = 0;
  for (const ts of timeSeries) {
    for (const point of ts.points ?? []) {
      const val = point.value?.int64Value;
      if (val != null) total += Number(val);
    }
  }
  return total;
}

async function sendDigestEmail(
  adminEmail: string,
  apiKey: string,
  newUsers: number,
  authCallbacks: number,
  emailNotifies: number,
  fromEmail: string,
): Promise<void> {
  const subject = `Refactor Agent - Daily digest: ${newUsers} new users, ${authCallbacks} auth callbacks, ${emailNotifies} emails sent`;
  const html = `<p>Daily usage digest (last 24h):</p>
<ul>
<li><strong>New users:</strong> ${newUsers}</li>
<li><strong>Auth callbacks:</strong> ${authCallbacks}</li>
<li><strong>Email notifications:</strong> ${emailNotifies}</li>
</ul>`;

  const res = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
      "User-Agent": "refactor-agent-usage-digest/1.0",
    },
    body: JSON.stringify({
      from: fromEmail,
      to: [adminEmail],
      subject,
      html,
    }),
  });

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Resend API error: ${res.status} ${body}`);
  }
  const result = (await res.json()) as { id?: string };
  console.log("Resend sent digest to=%s id=%s", adminEmail, result.id);
}

const handler = httpHandler(async (req, _res): Promise<HttpResponse> => {
  const adminEmail = process.env["ADMIN_EMAIL"];
  const apiKey = process.env["RESEND_API_KEY"];
  const projectId =
    process.env["GOOGLE_CLOUD_PROJECT"] ?? process.env["GCP_PROJECT"];
  const fromEmail =
    process.env["FROM_EMAIL"] ?? "Refactor Agent <noreply@refactorum.com>";

  console.log(
    "usage_digest started admin=%s project=%s",
    adminEmail ?? "(unset)",
    projectId ?? "(unset)",
  );

  if (!adminEmail || !apiKey || !projectId) {
    console.error(
      "Missing config: admin=%s api_key=%s project=%s",
      Boolean(adminEmail),
      Boolean(apiKey),
      Boolean(projectId),
    );
    return {
      body: "Missing ADMIN_EMAIL, RESEND_API_KEY, or project",
      status: 500,
    };
  }

  const endTime = new Date();
  const startTime = new Date(endTime.getTime() - 24 * 60 * 60 * 1000);

  const newUsers = await countNewUsers(projectId);
  const client = new MetricServiceClient();
  const authCallbacks = await getRequestCount(
    projectId,
    client,
    "auth-github-callback",
    startTime,
    endTime,
  );
  const emailNotifies = await getRequestCount(
    projectId,
    client,
    "email-notify-pending-user",
    startTime,
    endTime,
  );

  console.log(
    "Sending digest: users=%s auth=%s emails=%s",
    newUsers,
    authCallbacks,
    emailNotifies,
  );

  await sendDigestEmail(
    adminEmail,
    apiKey,
    newUsers,
    authCallbacks,
    emailNotifies,
    fromEmail,
  );

  return {
    body: "OK",
    status: 200,
    headers: { "Content-Type": "text/plain" },
  };
});

http("usageDigest", handler);

export { handler as usageDigest };
