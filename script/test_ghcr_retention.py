"""Offline tests: python -B -m unittest discover -s script -p test_ghcr_retention.py"""
from datetime import datetime, timedelta, timezone
import os
import unittest
from unittest.mock import patch

import ghcr_retention
from ghcr_retention import plan

NOW = datetime(2026, 10, 16, tzinfo=timezone.utc)


def version(vid, tags, days_old, digest=None):
    return {"id": vid, "name": digest or f"sha256:{vid:064x}",
            "created_at": (NOW - timedelta(days=days_old)).isoformat().replace("+00:00", "Z"),
            "metadata": {"container": {"tags": tags}}}


def ids(items):
    return sorted(v["id"] for v in items)


class RetentionPlanTests(unittest.TestCase):
    def test_protected_tags_are_never_deleted(self):
        versions = [version(1, ["1.2.0", "1.2", "sha-aaaaaaa"], 400), version(2, ["main", "sha-bbbbbbb"], 400),
                    version(3, ["develop"], 400), version(4, ["refractor", "sha-ccccccc"], 400)]
        roots, untagged, _ = plan(versions, lambda d: [], NOW, keep_latest=0)
        self.assertEqual((roots, untagged), ([], []))

    def test_old_sha_only_deleted_beyond_keep_latest(self):
        versions = [version(i, [f"sha-{i:07x}"], 40 + i) for i in range(1, 6)]
        roots, _, _ = plan(versions, lambda d: [], NOW, keep_latest=2)
        self.assertEqual(ids(roots), [3, 4, 5])

    def test_young_sha_only_kept_even_beyond_keep_latest(self):
        versions = [version(i, [f"sha-{i:07x}"], i) for i in range(1, 6)]
        roots, _, _ = plan(versions, lambda d: [], NOW, keep_latest=1)
        self.assertEqual(roots, [])

    def test_children_follow_their_index_but_shared_children_stay(self):
        old = version(1, ["sha-aaaaaaa"], 90, digest="sha256:old")
        kept = version(2, ["main", "sha-bbbbbbb"], 1, digest="sha256:kept")
        only_old = version(3, [], 90, digest="sha256:only-old")
        shared = version(4, [], 90, digest="sha256:shared")
        kept_child = version(5, [], 90, digest="sha256:kept-child")
        tree = {"sha256:old": ["sha256:only-old", "sha256:shared"], "sha256:kept": ["sha256:shared", "sha256:kept-child"]}
        roots, untagged, _ = plan([old, kept, only_old, shared, kept_child], lambda d: tree.get(d, []), NOW, keep_latest=0)
        self.assertEqual(ids(roots), [1])
        self.assertEqual(ids(untagged), [3])

    def test_young_child_of_deleted_index_is_deleted_with_it(self):
        old = version(1, ["sha-aaaaaaa"], 90, digest="sha256:old")
        child = version(2, [], 0, digest="sha256:child")
        roots, untagged, _ = plan([old, child], lambda d: ["sha256:child"] if d == "sha256:old" else [], NOW, keep_latest=0)
        self.assertEqual((ids(roots), ids(untagged)), ([1], [2]))

    def test_orphans_deleted_only_when_old(self):
        versions = [version(1, [], 90), version(2, [], 3)]
        _, untagged, _ = plan(versions, lambda d: [], NOW)
        self.assertEqual(ids(untagged), [1])

    def test_unreadable_kept_manifest_blocks_all_untagged_deletes(self):
        kept = version(1, ["main"], 1, digest="sha256:kept")
        orphan = version(2, [], 90)

        def children(digest):
            raise OSError("registry down")
        roots, untagged, notes = plan([kept, orphan], children, NOW)
        self.assertEqual((roots, untagged), ([], []))
        self.assertTrue(notes)

    def test_short_or_odd_sha_tags_count_as_protected(self):
        versions = [version(1, ["sha-abc"], 400), version(2, ["sha-zzzzzzz"], 400)]
        roots, _, _ = plan(versions, lambda d: [], NOW, keep_latest=0)
        self.assertEqual(roots, [])


class RetentionMainTests(unittest.TestCase):
    def run_main(self, apply):
        class FakeGhcr:
            deleted = []

            def __init__(self, *args):
                pass

            def versions(self, package):
                return [version(1, ["sha-aaaaaaa"], 400), version(2, ["main"], 1)]

            def children(self, package, digest):
                return []

            def delete(self, package, version_id):
                FakeGhcr.deleted.append(version_id)

        env = {"OWNER": "o", "PACKAGES": "p", "GITHUB_TOKEN": "t", "KEEP_LATEST": "0", "APPLY": apply}
        with patch.object(ghcr_retention, "Ghcr", FakeGhcr), patch.dict(os.environ, env, clear=True), \
                patch("builtins.print"):
            self.assertEqual(ghcr_retention.main(), 0)
        return FakeGhcr.deleted

    def test_dry_run_never_deletes(self):
        self.assertEqual(self.run_main("false"), [])

    def test_apply_deletes_only_planned(self):
        self.assertEqual(self.run_main("true"), [1])


if __name__ == "__main__":
    unittest.main()
