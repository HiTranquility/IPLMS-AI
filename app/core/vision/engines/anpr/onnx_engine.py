"""Adapter tăng tốc ANPR Object Detection sử dụng ONNX Runtime.

Tối ưu độ trễ siêu tốc (<30ms per frame trên CPU/GPU) với cơ chế
fallback an toàn sang PyTorch engine nếu chưa có file model ONNX
hoặc chưa cài đặt thư viện `onnxruntime`.
"""
import os
from pathlib import Path
import threading
import time
from typing import Any, List, Optional, Tuple, Union

import cv2
import numpy as np

from app.config import get_config
from app.core.exceptions import PlateRecognitionError
from app.core.vision.engines.anpr import detector as anpr_detector
from app.util.logger import logger

AI_ROOT = Path(__file__).resolve().parents[5]

try:
    import onnxruntime as ort
    HAS_ONNXRUNTIME = True
except (ImportError, ModuleNotFoundError):
    ort = None
    HAS_ONNXRUNTIME = False


class AnprOnnxEngine:
    """ONNX Runtime Adapter for ANPR Plate Detection with PyTorch Fallback."""

    def __init__(
        self,
        model_path: Optional[Union[str, Path]] = None,
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        input_size: Tuple[int, int] = (640, 640),
        providers: Optional[List[str]] = None,
    ):
        """Khởi tạo ONNX Engine.

        Args:
            model_path: Đường dẫn tới file model `.onnx` hoặc `best.onnx`.
                Nếu None, sẽ tự động tìm kiếm trong các thư mục cấu hình và dự án.
            conf_threshold: Ngưỡng tự tin tối thiểu để chấp nhận box phát hiện.
            iou_threshold: Ngưỡng IoU cho Non-Maximum Suppression (NMS).
            input_size: Kích thước đầu vào chuẩn (width, height) cho model YOLO ONNX.
            providers: Danh sách Execution Providers của ONNX Runtime.
        """
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.input_size = input_size
        self.session: Optional[Any] = None
        self.input_name: Optional[str] = None
        self.output_names: List[str] = []
        self.resolved_onnx_path: Optional[Path] = None
        self.is_onnx_available: bool = False
        self._fallback_detector = None
        self._configured_model_path = model_path
        self._configured_providers = providers
        self._session_lock = threading.Lock()
        self._load_attempted: bool = False

        if not self._is_onnx_enabled_in_config():
            logger.info("ONNX engine disabled via VisionConfig.onnx_enabled=false. Operating in PyTorch fallback mode.")
            return

        self._try_load_session()

    @staticmethod
    def _is_onnx_enabled_in_config() -> bool:
        """Đọc cờ onnx_enabled trực tiếp từ cấu hình hiện hành (hỗ trợ bật/tắt nóng từ AI Console)."""
        try:
            vision = get_config().vision
            if vision is not None:
                return bool(vision.onnx_enabled)
        except Exception:
            pass
        return True

    def _try_load_session(self) -> bool:
        """Nạp lười ONNX InferenceSession có khóa luồng (AI_CONVENTIONS §6)."""
        with self._session_lock:
            if self.is_onnx_available and self.session is not None:
                return True
            self._load_attempted = True
            resolved = self._resolve_model_path(self._configured_model_path)
            if HAS_ONNXRUNTIME and resolved is not None and resolved.exists():
                try:
                    self._init_session(resolved, self._configured_providers)
                    self.resolved_onnx_path = resolved
                    self.is_onnx_available = True
                    logger.info(f"AnprOnnxEngine initialized successfully with model: {resolved}")
                    return True
                except Exception as exc:
                    logger.warning(f"Failed to initialize ONNX session ({exc}). Falling back to PyTorch.")
                    self.is_onnx_available = False
                    return False

            if not HAS_ONNXRUNTIME:
                logger.info("onnxruntime is not installed. AnprOnnxEngine operates in PyTorch fallback mode.")
            elif resolved is None or not resolved.exists():
                logger.info(f"ONNX model file not found ({resolved}). AnprOnnxEngine operates in PyTorch fallback mode.")
            self.is_onnx_available = False
            return False

    def _resolve_model_path(self, model_path: Optional[Union[str, Path]]) -> Optional[Path]:
        """Tìm kiếm file model .onnx trong cấu hình VisionConfig và các thư mục dự án."""
        if model_path is not None:
            p = Path(model_path)
            if p.exists():
                return p
            if p.suffix != ".onnx":
                onnx_candidate = p.with_suffix(".onnx")
                if onnx_candidate.exists():
                    return onnx_candidate
            return None

        try:
            vision = get_config().vision
            if vision:
                if getattr(vision, "onnx_model_dir", None):
                    cfg_dir = Path(vision.onnx_model_dir)
                    base_dirs = [cfg_dir] if cfg_dir.is_absolute() else [cfg_dir, AI_ROOT / cfg_dir]
                    for b_dir in base_dirs:
                        if b_dir.is_file() and b_dir.suffix == ".onnx" and b_dir.exists():
                            return b_dir
                        for candidate_name in ("best.onnx", "model.onnx", "yolov8n.onnx"):
                            cand = b_dir / candidate_name
                            if cand.exists():
                                return cand
                if getattr(vision, "yolo_model_path", None):
                    cfg_path = Path(vision.yolo_model_path)
                    path_variants = [cfg_path] if cfg_path.is_absolute() else [cfg_path, AI_ROOT / cfg_path]
                    for p_var in path_variants:
                        if p_var.suffix == ".onnx" and p_var.exists():
                            return p_var
                        onnx_variant = p_var.with_suffix(".onnx")
                        if onnx_variant.exists():
                            return onnx_variant
        except Exception:
            pass

        search_candidates = [
            AI_ROOT / "data" / "models" / "best.onnx",
            Path("data/models/best.onnx"),
            AI_ROOT / "model" / "artifacts" / "bootstrap" / "anpr" / "best.onnx",
            Path("model/artifacts/bootstrap/anpr/best.onnx"),
            Path("best.onnx"),
        ]
        for candidate in search_candidates:
            if candidate.exists():
                return candidate

        return None

    def _init_session(self, model_path: Path, providers: Optional[List[str]] = None) -> None:
        """Khởi tạo ONNX session với thiết lập tối ưu hóa độ trễ."""
        sess_options = ort.SessionOptions()
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        sess_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        # Cho phép đa luồng nội bộ để xử lý nhanh nhất trên CPU
        sess_options.intra_op_num_threads = min(4, os.cpu_count() or 4)

        available_providers = ort.get_available_providers()
        chosen_providers = []
        if providers:
            chosen_providers = [p for p in providers if p in available_providers]
        if not chosen_providers:
            if "CUDAExecutionProvider" in available_providers:
                chosen_providers.append("CUDAExecutionProvider")
            if "CPUExecutionProvider" in available_providers:
                chosen_providers.append("CPUExecutionProvider")

        self.session = ort.InferenceSession(
            str(model_path),
            sess_options=sess_options,
            providers=chosen_providers,
        )
        self.input_name = self.session.get_inputs()[0].name
        self.output_names = [out.name for out in self.session.get_outputs()]

    def is_using_onnx(self) -> bool:
        """Kiểm tra xem engine hiện đang dùng ONNX Runtime hay PyTorch Fallback."""
        if not self._is_onnx_enabled_in_config():
            return False
        if self.is_onnx_available and self.session is not None:
            return True
        if not self._load_attempted:
            return self._try_load_session()
        return False

    def _preprocess(self, img_cv: np.ndarray) -> Tuple[np.ndarray, float, Tuple[int, int]]:
        """Letterbox resize và chuẩn hóa ảnh sang dạng NCHW float32.

        Returns:
            Tuple (input_tensor, scale_ratio, (pad_left, pad_top))
        """
        orig_h, orig_w = img_cv.shape[:2]
        target_w, target_h = self.input_size

        scale = min(target_w / orig_w, target_h / orig_h)
        new_w, new_h = int(round(orig_w * scale)), int(round(orig_h * scale))

        resized = cv2.resize(img_cv, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        pad_w = target_w - new_w
        pad_h = target_h - new_h
        pad_left = pad_w // 2
        pad_right = pad_w - pad_left
        pad_top = pad_h // 2
        pad_bottom = pad_h - pad_top

        # Pad màu xám 114 chuẩn của YOLO
        padded = cv2.copyMakeBorder(
            resized, pad_top, pad_bottom, pad_left, pad_right,
            cv2.BORDER_CONSTANT, value=(114, 114, 114)
        )

        # Chuyển BGR -> RGB -> Float32 [0.0, 1.0] -> CHW -> NCHW
        img_rgb = cv2.cvtColor(padded, cv2.COLOR_BGR2RGB)
        tensor = img_rgb.astype(np.float32) / 255.0
        tensor = np.transpose(tensor, (2, 0, 1))
        tensor = np.expand_dims(tensor, axis=0)

        return tensor, scale, (pad_left, pad_top)

    def _postprocess(
        self,
        outputs: List[np.ndarray],
        orig_shape: Tuple[int, int],
        scale: float,
        pad: Tuple[int, int],
    ) -> Tuple[List[Tuple[int, int, int, int]], List[float]]:
        """Giải mã kết quả từ ONNX model và áp dụng NMS.

        Returns:
            Tuple (boxes, confidences) với boxes là [(x1, y1, x2, y2), ...]
        """
        raw_output = outputs[0]
        # YOLOv8 format thông thường: (1, 84, 8400) hoặc (1, 5, 8400)
        # Transpose về (1, 8400, C) nếu cần
        if len(raw_output.shape) == 3 and raw_output.shape[1] < raw_output.shape[2]:
            raw_output = np.transpose(raw_output, (0, 2, 1))

        preds = raw_output[0]  # shape (N, C)
        orig_h, orig_w = orig_shape
        pad_left, pad_top = pad

        if len(preds) == 0:
            return [], []

        # Tối ưu vector hóa: lọc các box vượt ngưỡng conf_threshold bằng NumPy
        if preds.shape[1] > 5:
            scores = np.max(preds[:, 4:], axis=1)
        else:
            scores = preds[:, 4]

        mask = scores >= self.conf_threshold
        valid_preds = preds[mask]
        valid_scores = scores[mask]

        if len(valid_preds) == 0:
            return [], []

        cx = valid_preds[:, 0]
        cy = valid_preds[:, 1]
        w = valid_preds[:, 2]
        h = valid_preds[:, 3]

        x1 = cx - w / 2.0
        y1 = cy - h / 2.0

        orig_x1 = np.round((x1 - pad_left) / scale).astype(int)
        orig_y1 = np.round((y1 - pad_top) / scale).astype(int)
        orig_w_box = np.round(w / scale).astype(int)
        orig_h_box = np.round(h / scale).astype(int)

        orig_x1 = np.clip(orig_x1, 0, orig_w)
        orig_y1 = np.clip(orig_y1, 0, orig_h)
        orig_w_box = np.clip(orig_w_box, 0, orig_w - orig_x1)
        orig_h_box = np.clip(orig_h_box, 0, orig_h - orig_y1)

        boxes_list = []
        scores_list = []
        for i in range(len(valid_preds)):
            bw, bh = int(orig_w_box[i]), int(orig_h_box[i])
            if bw > 0 and bh > 0:
                boxes_list.append([int(orig_x1[i]), int(orig_y1[i]), bw, bh])
                scores_list.append(float(valid_scores[i]))

        if not boxes_list:
            return [], []

        # Áp dụng OpenCV NMS
        indices = cv2.dnn.NMSBoxes(boxes_list, scores_list, self.conf_threshold, self.iou_threshold)
        final_boxes = []
        final_confs = []

        if len(indices) > 0:
            for idx in indices.flatten():
                x, y, w, h = boxes_list[idx]
                final_boxes.append((x, y, x + w, y + h))
                final_confs.append(scores_list[idx])

        return final_boxes, final_confs

    def detect_plate(self, img_cv: np.ndarray) -> Tuple[np.ndarray, Optional[float]]:
        """Phát hiện vùng biển số bằng ONNX session (với PyTorch fallback tự động).

        Args:
            img_cv: Ảnh gốc BGR dạng numpy ndarray.

        Returns:
            Tuple (crop_image, confidence). Nếu không phát hiện được biển, ném PlateRecognitionError.
        """
        if self.is_using_onnx():
            try:
                start_t = time.perf_counter()
                tensor, scale, pad = self._preprocess(img_cv)
                outputs = self.session.run(self.output_names, {self.input_name: tensor})
                boxes, confs = self._postprocess(outputs, img_cv.shape[:2], scale, pad)
                duration_ms = (time.perf_counter() - start_t) * 1000.0

                logger.debug(f"ONNX ANPR detection executed in {duration_ms:.2f}ms (boxes={len(boxes)})")

                if boxes:
                    # Lấy box có điểm tin cậy cao nhất
                    best_idx = int(np.argmax(confs))
                    x1, y1, x2, y2 = boxes[best_idx]
                    crop = img_cv[y1:y2, x1:x2]
                    return crop, float(confs[best_idx])
                else:
                    raise PlateRecognitionError("Không phát hiện được biển số qua ONNX detector")
            except PlateRecognitionError:
                raise
            except Exception as exc:
                logger.warning(f"ONNX inference failed ({exc}). Retrying with PyTorch fallback engine.")
                return self._fallback_pytorch_detect(img_cv)

        return self._fallback_pytorch_detect(img_cv)

    def _fallback_pytorch_detect(self, img_cv: np.ndarray) -> Tuple[np.ndarray, Optional[float]]:
        """Fallback an toàn sang PyTorch engine (ultralytics YOLO) hiện tại."""
        try:
            return anpr_detector.detect_plate(img_cv)
        except Exception as exc:
            if isinstance(exc, PlateRecognitionError):
                raise
            logger.error(f"PyTorch detector fallback error: {exc}")
            raise PlateRecognitionError(f"Cả ONNX và PyTorch detector đều thất bại: {exc}")

    def measure_latency(self, dummy_img: Optional[np.ndarray] = None, iterations: int = 5) -> float:
        """Đo độ trễ trung bình của engine tính bằng milliseconds (ms)."""
        if dummy_img is None:
            dummy_img = np.full((480, 640, 3), 128, dtype=np.uint8)

        times = []
        for _ in range(iterations):
            t0 = time.perf_counter()
            try:
                self.detect_plate(dummy_img)
            except Exception:
                pass
            times.append((time.perf_counter() - t0) * 1000.0)

        avg_latency = sum(times) / len(times) if times else 0.0
        return round(avg_latency, 2)
