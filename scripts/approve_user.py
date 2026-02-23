#!/usr/bin/env -S uv run python
"""Admin CLI: list pending users, approve, or ban. Uses Firestore via ADC.

Usage:
  uv run python scripts/approve_user.py <github_login>          # approve
  uv run python scripts/approve_user.py <github_login> --ban    # ban
  uv run python scripts/approve_user.py --list pending          # show pending requests
"""

from __future__ import annotations

import argparse
import os
import sys

from google.cloud.firestore import FieldFilter


def _get_firestore():
    from google.cloud import firestore

    project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCLOUD_PROJECT")
    if not project:
        print("Set GOOGLE_CLOUD_PROJECT or GCLOUD_PROJECT", file=sys.stderr)
        sys.exit(1)
    return firestore.Client(project=project)


def list_pending(db) -> None:
    users = (
        db.collection("users")
        .where(filter=FieldFilter("status", "==", "pending"))
        .stream()
    )
    rows = []
    for doc in users:
        d = doc.to_dict()
        rows.append((d.get("github_login", "?"), d.get("email", "-"), doc.id))
    if not rows:
        print("No pending requests.")
        return
    for login, email, uid in sorted(rows, key=lambda r: r[0]):
        print(f"  {login}  {email}  (id={uid})")


def approve(db, github_login: str) -> None:
    users = (
        db.collection("users")
        .where(filter=FieldFilter("github_login", "==", github_login))
        .limit(1)
        .stream()
    )
    doc = next(users, None)
    if not doc:
        print(f"User not found: {github_login}", file=sys.stderr)
        sys.exit(1)
    doc.reference.update({"status": "active"})
    print(f"Approved: {github_login}")


def ban(db, github_login: str) -> None:
    users = (
        db.collection("users")
        .where(filter=FieldFilter("github_login", "==", github_login))
        .limit(1)
        .stream()
    )
    doc = next(users, None)
    if not doc:
        print(f"User not found: {github_login}", file=sys.stderr)
        sys.exit(1)
    doc.reference.update({"status": "banned", "ban_reason": "Banned by admin"})
    print(f"Banned: {github_login}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Approve or ban alpha users")
    parser.add_argument("github_login", nargs="?", help="GitHub login to act on")
    parser.add_argument("--list", choices=["pending"], help="List pending users")
    parser.add_argument("--ban", action="store_true", help="Ban instead of approve")
    args = parser.parse_args()

    db = _get_firestore()

    if args.list:
        if args.list == "pending":
            list_pending(db)
        return

    if not args.github_login:
        parser.error("github_login required (or use --list pending)")
    if args.ban:
        ban(db, args.github_login)
    else:
        approve(db, args.github_login)


if __name__ == "__main__":
    main()
