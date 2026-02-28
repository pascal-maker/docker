/** Firestore helpers for Cloud Functions. */

import { FieldValue, Firestore } from "@google-cloud/firestore";
import type { RepoAccess, RepoRef } from "./github.js";

const USERS_COLLECTION = "users";
const INSTALLATION_USERS_COLLECTION = "installation_users";

/** Firestore document shape for allowed_repos (repo objects with id and full_name). */
interface AllowedRepoDoc {
  id: number;
  full_name: string;
}

/**
 * Add and remove repos from a user's allowed_repos in Firestore.
 */
export async function updateUserRepos(
  projectId: string,
  userId: string,
  toAdd: RepoRef[],
  toRemove: RepoRef[],
): Promise<void> {
  const db = new Firestore({ projectId });

  const docRef = db.collection(USERS_COLLECTION).doc(userId);
  const doc = await docRef.get();
  if (!doc.exists) {
    return;
  }

  const data = doc.data() ?? {};
  const current = (data["allowed_repos"] ?? []) as AllowedRepoDoc[];
  const removeIds = new Set(toRemove.map((r) => r.id));

  let updated = current.filter((r) => !removeIds.has(r.id));
  const addMap = new Map(toAdd.map((r) => [r.id, r]));

  for (const r of updated) {
    addMap.delete(r.id);
  }
  for (const r of addMap.values()) {
    updated.push({ id: r.id, full_name: r.full_name });
  }

  await docRef.update({ allowed_repos: updated });
}

/**
 * Get user IDs for an installation from Firestore.
 */
export async function getInstallationUserIds(
  projectId: string,
  installationId: number,
): Promise<string[]> {
  const db = new Firestore({ projectId });

  const instRef = db
    .collection(INSTALLATION_USERS_COLLECTION)
    .doc(String(installationId));
  const instDoc = await instRef.get();
  if (!instDoc.exists) {
    return [];
  }

  const data = instDoc.data() ?? {};
  const userIds = data["user_ids"];
  if (!Array.isArray(userIds)) {
    return [];
  }
  return userIds.map((id: unknown) => String(id));
}

/**
 * Create or update user in Firestore with status and allowed_repos.
 * For new users: status=pending, created_at=serverTimestamp.
 */
export async function writeUserToFirestore(
  projectId: string,
  userId: string,
  login: string,
  email: string | null,
  allowedRepos: RepoAccess[],
  installationIds: number[],
): Promise<void> {
  const db = new Firestore({ projectId });

  const docRef = db.collection(USERS_COLLECTION).doc(userId);
  const doc = await docRef.get();

  const payload: Record<string, unknown> = {
    github_login: login,
    email: email,
    allowed_repos: allowedRepos.map((r) => ({
      id: r.id,
      full_name: r.full_name,
    })),
  };

  if (!doc.exists) {
    payload["created_at"] = FieldValue.serverTimestamp();
    payload["status"] = "pending";
    await docRef.set(payload);
  } else {
    await docRef.update(payload);
  }

  for (const instId of installationIds) {
    const instRef = db
      .collection(INSTALLATION_USERS_COLLECTION)
      .doc(String(instId));
    const instDoc = await instRef.get();
    let existing: string[] = [];
    if (instDoc.exists) {
      const data = instDoc.data() ?? {};
      const userIds = data["user_ids"];
      existing = Array.isArray(userIds)
        ? userIds.map((id: unknown) => String(id))
        : [];
    }
    if (!existing.includes(userId)) {
      existing.push(userId);
    }
    await instRef.set({ user_ids: existing });
  }
}
