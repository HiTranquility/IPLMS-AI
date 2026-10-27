"""Prove the Dockerfile-specific allowlist with a synthetic, network-free image."""
import io
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest
import uuid


@unittest.skipUnless(os.environ.get("AI_RUN_CONTEXT_FIXTURE") == "1", "Opt-in Docker fixture only")
class DockerContextTest(unittest.TestCase):
    def test_runtime_data_is_excluded_by_actual_builder(self):
        if not shutil.which("docker"):
            self.skipTest("Docker CLI unavailable")
        daemon = subprocess.run(["docker", "info", "--format", "{{.OSType}}"], capture_output=True, timeout=10)
        if daemon.returncode:
            self.skipTest("Docker daemon unavailable; no services were started")
        base = Path(tempfile.gettempdir()).resolve()
        context = Path(tempfile.mkdtemp(prefix="iplms-context-proof-", dir=base)).resolve()
        self.assertEqual(context.parent, base)
        self.assertTrue(context.name.startswith("iplms-context-proof-"))
        tag = "iplms-context-proof:" + uuid.uuid4().hex[:12]
        name = "iplms-context-proof-" + uuid.uuid4().hex[:12]
        allowed = {"ai/app/probe.py":"pass", "ai/requirements-service.txt":"# fixture", "ai/static/cropped/.gitkeep":"", "ai/data/prompts/probe_v1.txt":"prompt", "proto/probe.proto":"syntax = \"proto3\";"}
        excluded = ["ai/static/original/", "ai/static/cropped/", "ai/data/golden/", "ai/data/datalake/", "ai/model/checkpoint/", "ai/.venv/", "other/"]
        for parent in excluded:
            allowed[parent + "private-fixture.txt"] = "synthetic exclusion sentinel"
        try:
            for relative, text in allowed.items():
                p = context / relative; p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(text, encoding="utf-8")
            dockerfile = context / "ai/Dockerfile"
            dockerfile.write_text("FROM scratch\nCOPY . /\n", encoding="utf-8")
            ignore = Path(__file__).resolve().parents[1] / "Dockerfile.dockerignore"
            (context / "ai/Dockerfile.dockerignore").write_bytes(ignore.read_bytes())
            build = subprocess.run(["docker","build","--network=none","--no-cache","-q","-t",tag,"-f",str(dockerfile),str(context)], text=True, capture_output=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            subprocess.run(["docker","create","--name",name,tag,"/unused"], check=True, capture_output=True)
            export = subprocess.run(["docker","export",name], check=True, capture_output=True)
            with tarfile.open(fileobj=io.BytesIO(export.stdout)) as archive:
                names = archive.getnames()
            self.assertFalse([n for n in names if n.endswith("private-fixture.txt")])
            self.assertIn("ai/app/probe.py", names)
            self.assertIn("ai/static/cropped/.gitkeep", names)
            self.assertIn("ai/data/prompts/probe_v1.txt", names)  # bug-042
            self.assertIn("proto/probe.proto", names)
        finally:
            subprocess.run(["docker","rm",name], capture_output=True)
            subprocess.run(["docker","image","rm",tag], capture_output=True)
            # This directory contains only synthetic files made by this test.
            assert context.parent == base and context.name.startswith("iplms-context-proof-")
            shutil.rmtree(context)


if __name__ == "__main__":unittest.main()
