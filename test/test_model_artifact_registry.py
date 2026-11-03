"""Kiểm tra resolve local, tải signed URL và cache model theo version/hash."""
import hashlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.infra.model_registry import (
    ArtifactResolutionError,
    ArtifactStore,
    ModelArtifactSpec,
)


class _FakeResponse(io.BytesIO):
    def __init__(self, content: bytes) -> None:
        super().__init__(content)
        self.headers = {"Content-Length": str(len(content))}


class ArtifactStoreTest(unittest.TestCase):
    def _registry(self, root: Path) -> ArtifactStore:
        return ArtifactStore(
            ai_root=root,
            cache_dir="var/model-cache",
            timeout_seconds=10,
            max_bytes=1024,
            allow_insecure_http=True,
        )

    def test_resolve_relative_local_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "model" / "model.pth"
            artifact.parent.mkdir(parents=True)
            artifact.write_bytes(b"checkpoint")

            resolved = self._registry(root).resolve(
                ModelArtifactSpec(
                    name="vehicle-classifier",
                    version="v1",
                    file_name="model.pth",
                    local_path="model/model.pth",
                )
            )

            self.assertEqual(resolved.resolve(), artifact.resolve())

    def test_download_once_then_reuse_verified_cache(self):
        content = b"model artifact"
        checksum = hashlib.sha256(content).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            registry = self._registry(Path(directory))
            spec = ModelArtifactSpec(
                name="vehicle-classifier",
                version="2026-09-19.1",
                file_name="model.pth",
                source_url="http://minio.local/signed-model-url",
                sha256=checksum,
            )

            with patch(
                "app.infra.storage.object_store.urlopen",
                return_value=_FakeResponse(content),
            ) as mocked_urlopen:
                first_path = registry.resolve(spec)
                second_path = registry.resolve(spec)

            self.assertEqual(first_path, second_path)
            self.assertEqual(first_path.read_bytes(), content)
            mocked_urlopen.assert_called_once()

    def test_remote_url_duoc_uu_tien_hon_local_bootstrap(self):
        remote_content = b"accepted model"
        checksum = hashlib.sha256(remote_content).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            local_path = root / "model" / "bootstrap.pth"
            local_path.parent.mkdir(parents=True)
            local_path.write_bytes(b"old bootstrap")

            with patch(
                "app.infra.storage.object_store.urlopen",
                return_value=_FakeResponse(remote_content),
            ):
                resolved = self._registry(root).resolve(
                    ModelArtifactSpec(
                        name="vehicle-classifier",
                        version="accepted-v2",
                        file_name="model.pth",
                        local_path="model/bootstrap.pth",
                        source_url="http://minio.local/signed-model-url",
                        sha256=checksum,
                    )
                )

            self.assertNotEqual(resolved, local_path)
            self.assertEqual(resolved.read_bytes(), remote_content)

    def test_reject_remote_artifact_without_sha256(self):
        with tempfile.TemporaryDirectory() as directory:
            registry = self._registry(Path(directory))
            with self.assertRaisesRegex(ArtifactResolutionError, "SHA-256"):
                registry.resolve(
                    ModelArtifactSpec(
                        name="plate-detector",
                        version="v1",
                        file_name="best.pt",
                        source_url="http://minio.local/signed-model-url",
                    )
                )

    def test_reject_path_segments_in_artifact_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            registry = self._registry(Path(directory))
            with self.assertRaisesRegex(ArtifactResolutionError, "Invalid model artifact"):
                registry.resolve(
                    ModelArtifactSpec(
                        name="../escape",
                        version="v1",
                        file_name="model.pth",
                        source_url="http://minio.local/signed-model-url",
                        sha256="0" * 64,
                    )
                )


if __name__ == "__main__":
    unittest.main()
