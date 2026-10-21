#!/usr/bin/env python3
"""Prune old GHCR image versions (umbrella IPLMS ADR-0027 §retention). Stdlib only.

Keeps forever: any version with a tag that is not ``sha-<hex>`` (semver, main,
develop, legacy aliases such as ``refractor``).
Deletes: versions whose tags are all ``sha-*`` once they are older than
MAX_AGE_DAYS and not among the KEEP_LATEST newest of them, plus their child
manifests (per-platform images, SBOM/provenance attestations) that no kept
version references. Untagged versions not reachable from any tagged version
are deleted once older than MAX_AGE_DAYS.

[GOTCHA] BuildKit stores attestations as *untagged* child manifests of the
image index. "Delete all untagged versions" — the usual recipe — breaks every
image that has an SBOM. Children are only deleted when no kept index lists them,
and nothing untagged is deleted if a kept index cannot be read.

Dry run unless APPLY=true. Env: OWNER, PACKAGES (space separated), GITHUB_TOKEN,
optional OWNER_TYPE (users|orgs, default users), MAX_AGE_DAYS (30), KEEP_LATEST (10).
"""
import base64
from datetime import datetime, timedelta, timezone
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

SHA_TAG = re.compile(r"sha-[0-9a-f]{7,40}\Z")
MANIFEST_TYPES = ", ".join([
    "application/vnd.oci.image.index.v1+json",
    "application/vnd.docker.distribution.manifest.list.v2+json",
    "application/vnd.oci.image.manifest.v1+json",
    "application/vnd.docker.distribution.manifest.v2+json",
])


def tags_of(version):
    return version.get("metadata", {}).get("container", {}).get("tags", [])


def created(version):
    return datetime.fromisoformat(version["created_at"].replace("Z", "+00:00"))


def plan(versions, children_of, now, max_age_days=30, keep_latest=10):
    """Pure decision step. children_of(digest) -> list of child digests (raises on failure).

    Returns (delete_roots, delete_untagged, notes)."""
    cutoff = now - timedelta(days=max_age_days)
    tagged = [v for v in versions if tags_of(v)]
    sha_only = sorted((v for v in tagged if all(SHA_TAG.match(t) for t in tags_of(v))),
                      key=created, reverse=True)
    delete_roots = [v for v in sha_only[keep_latest:] if created(v) < cutoff]
    doomed = {v["id"] for v in delete_roots}
    kept_roots = [v for v in tagged if v["id"] not in doomed]
    notes = []

    def closure(digests):
        seen, stack = set(), list(digests)
        while stack:
            digest = stack.pop()
            for child in children_of(digest):
                if child not in seen:
                    seen.add(child)
                    stack.append(child)
        return seen

    try:
        kept_children = closure(v["name"] for v in kept_roots)
    except Exception as error:  # noqa: BLE001 — any failure means "do not touch untagged"
        notes.append(f"kept manifest unreadable ({error}); untagged versions left alone")
        return delete_roots, [], notes
    try:
        doomed_children = closure(v["name"] for v in delete_roots)
    except Exception as error:  # noqa: BLE001
        notes.append(f"manifest of a deleted version unreadable ({error}); its children left alone")
        doomed_children = set()

    delete_untagged = []
    for v in versions:
        if tags_of(v) or v["name"] in kept_children:
            continue
        if v["name"] in doomed_children or created(v) < cutoff:
            delete_untagged.append(v)
    return delete_roots, delete_untagged, notes


class Ghcr:
    def __init__(self, owner, token, owner_type="users"):
        self.owner, self.token, self.owner_type = owner, token, owner_type
        self._registry_tokens = {}

    def _api(self, method, path):
        request = urllib.request.Request(
            "https://api.github.com" + path, method=method,
            headers={"Authorization": f"Bearer {self.token}", "Accept": "application/vnd.github+json",
                     "X-GitHub-Api-Version": "2022-11-28"})
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read()
            return json.loads(body) if body else None

    def versions(self, package):
        result, page = [], 1
        base = f"/{self.owner_type}/{self.owner}/packages/container/{urllib.parse.quote(package)}/versions"
        while True:
            batch = self._api("GET", f"{base}?per_page=100&page={page}")
            result += batch
            if len(batch) < 100:
                return result
            page += 1

    def delete(self, package, version_id):
        self._api("DELETE", f"/{self.owner_type}/{self.owner}/packages/container/"
                            f"{urllib.parse.quote(package)}/versions/{version_id}")

    def children(self, package, digest):
        repo = f"{self.owner.lower()}/{package}"
        if repo not in self._registry_tokens:
            basic = base64.b64encode(f"token:{self.token}".encode()).decode()
            request = urllib.request.Request(
                f"https://ghcr.io/token?scope=repository:{repo}:pull",
                headers={"Authorization": f"Basic {basic}"})
            with urllib.request.urlopen(request, timeout=30) as response:
                self._registry_tokens[repo] = json.load(response)["token"]
        request = urllib.request.Request(
            f"https://ghcr.io/v2/{repo}/manifests/{digest}",
            headers={"Authorization": f"Bearer {self._registry_tokens[repo]}", "Accept": MANIFEST_TYPES})
        with urllib.request.urlopen(request, timeout=30) as response:
            manifest = json.load(response)
        return [m["digest"] for m in manifest.get("manifests", [])]


def main():
    apply = os.environ.get("APPLY", "").lower() == "true"
    max_age = int(os.environ.get("MAX_AGE_DAYS", "30"))
    keep = int(os.environ.get("KEEP_LATEST", "10"))
    ghcr = Ghcr(os.environ["OWNER"], os.environ["GITHUB_TOKEN"], os.environ.get("OWNER_TYPE", "users"))
    now = datetime.now(timezone.utc)
    lines = [f"### GHCR retention — {'APPLY' if apply else 'dry run'} "
             f"(sha-* older than {max_age}d beyond newest {keep}; semver/main/develop kept)", ""]
    failed = False
    for package in os.environ["PACKAGES"].split():
        try:
            versions = ghcr.versions(package)
        except urllib.error.HTTPError as error:
            lines.append(f"- `{package}`: cannot list versions (HTTP {error.code}) — package missing "
                         "or this repo lacks access")
            failed = True
            continue
        roots, untagged, notes = plan(versions, lambda d, p=package: ghcr.children(p, d), now, max_age, keep)
        lines.append(f"- `{package}`: {len(versions)} versions → delete {len(roots)} sha-only + "
                     f"{len(untagged)} untagged/child")
        lines += [f"  - note: {n}" for n in notes]
        for v in roots + untagged:
            label = ", ".join(tags_of(v)) or v["name"][:19]
            if not apply:
                lines.append(f"  - would delete {label} ({v['created_at'][:10]})")
                continue
            try:
                ghcr.delete(package, v["id"])
                lines.append(f"  - deleted {label}")
            except urllib.error.HTTPError as error:
                lines.append(f"  - FAILED {label}: HTTP {error.code} (repo needs Admin on the package)")
                failed = True
    report = "\n".join(lines)
    print(report)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write(report + "\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
