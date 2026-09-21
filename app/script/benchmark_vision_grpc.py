"""Measure Vision gRPC latency, errors, throughput and optional plate accuracy."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import grpc

from app.api.grpc.generated_stubs import get_stub
from app.utils.request_metrics import evaluate_gates, summarize_requests


_pb2, _pb2_grpc = get_stub("vision_service")


def _invoke(stub: Any, request: Any, *, index: int, timeout: float) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        response = stub.RecognizePlate(request, timeout=timeout)
        rtt_ms = (time.perf_counter() - started) * 1000
        server_ms = float(response.process_time_ms)
        return {
            "index": index,
            "ok": True,
            "grpc_status": "OK",
            "rtt_ms": rtt_ms,
            "server_process_ms": server_ms,
            "transport_overhead_ms": max(0.0, rtt_ms - server_ms),
            "plate_number": response.plate_number,
            "confidence": float(response.confidence),
            "vehicle_type": response.vehicle_type,
        }
    except grpc.RpcError as exc:
        return {
            "index": index,
            "ok": False,
            "grpc_status": exc.code().name,
            "rtt_ms": (time.perf_counter() - started) * 1000,
            "server_process_ms": 0.0,
            "transport_overhead_ms": 0.0,
            "error": exc.details(),
        }


def _default_report_path() -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return Path("data/benchmarks/vision") / f"vision-grpc-{stamp}.json"


def _synthetic_image_bytes(plate: str) -> bytes:
    import cv2
    import numpy as np

    canvas = np.full((300, 500, 3), 240, dtype=np.uint8)
    cv2.rectangle(canvas, (30, 40), (470, 260), (255, 255, 255), -1)
    cv2.rectangle(canvas, (30, 40), (470, 260), (0, 0, 0), 4)
    cv2.putText(
        canvas,
        plate,
        (55, 170),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.5,
        (10, 10, 10),
        4,
    )
    success, encoded = cv2.imencode(".jpg", canvas)
    if not success:
        raise RuntimeError("cannot encode synthetic benchmark image")
    return encoded.tobytes()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Benchmark VisionService.RecognizePlate using one fixed image."
    )
    image_source = parser.add_mutually_exclusive_group(required=True)
    image_source.add_argument("--image", type=Path)
    image_source.add_argument(
        "--synthetic-plate",
        help="generate a smoke-test image; never use it as production accuracy evidence",
    )
    parser.add_argument("--target", default="localhost:50051")
    parser.add_argument("--lane-id", default="benchmark_gate")
    parser.add_argument("--requests", type=int, default=20)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--warmup", type=int, default=2)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--classify-vehicle", action="store_true")
    parser.add_argument("--expected-plate")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--max-error-rate", type=float)
    parser.add_argument("--max-p95-ms", type=float)
    parser.add_argument("--min-normalized-match-rate", type=float)
    args = parser.parse_args()

    # Synthetic mode đã có nhãn ngay trong tham số. Gán trước validation để có
    # thể bật accuracy gate mà không buộc người dùng lặp lại cùng một giá trị ở
    # cả --synthetic-plate lẫn --expected-plate.
    if args.expected_plate is None and args.synthetic_plate:
        args.expected_plate = args.synthetic_plate

    if args.requests <= 0 or args.concurrency <= 0 or args.warmup < 0:
        parser.error("requests/concurrency must be positive and warmup cannot be negative")
    if args.timeout <= 0:
        parser.error("timeout must be positive")
    if args.min_normalized_match_rate is not None and not args.expected_plate:
        parser.error("--min-normalized-match-rate requires --expected-plate")
    for name in ("max_error_rate", "min_normalized_match_rate"):
        value = getattr(args, name)
        if value is not None and not 0 <= value <= 1:
            parser.error(f"--{name.replace('_', '-')} must be between 0 and 1")

    if args.image:
        image_path = args.image.resolve()
        if not image_path.is_file():
            parser.error(f"image not found: {image_path}")
        image_bytes = image_path.read_bytes()
        source_description = str(image_path)
    else:
        image_bytes = _synthetic_image_bytes(args.synthetic_plate)
        source_description = "synthetic"
    request = _pb2.RecognizePlateRequest(
        image_data=image_bytes,
        lane_id=args.lane_id,
        classify_vehicle=args.classify_vehicle,
    )

    channel = grpc.insecure_channel(
        args.target,
        options=[
            ("grpc.max_send_message_length", 10 * 1024 * 1024),
            ("grpc.max_receive_message_length", 10 * 1024 * 1024),
        ],
    )
    try:
        grpc.channel_ready_future(channel).result(timeout=args.timeout)
    except grpc.FutureTimeoutError:
        parser.error(f"gRPC target not ready within {args.timeout}s: {args.target}")
    stub = _pb2_grpc.VisionServiceStub(channel)

    warmup_samples = [
        _invoke(stub, request, index=-(index + 1), timeout=args.timeout)
        for index in range(args.warmup)
    ]
    started = time.perf_counter()
    samples: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = [
            executor.submit(_invoke, stub, request, index=index, timeout=args.timeout)
            for index in range(args.requests)
        ]
        for future in as_completed(futures):
            samples.append(future.result())
    wall_time = time.perf_counter() - started
    samples.sort(key=lambda row: int(row["index"]))

    summary = summarize_requests(
        samples,
        wall_time_seconds=wall_time,
        expected_plate=args.expected_plate,
    )
    gate_failures = evaluate_gates(
        summary,
        max_error_rate=args.max_error_rate,
        max_p95_ms=args.max_p95_ms,
        min_normalized_match_rate=args.min_normalized_match_rate,
    )
    if summary["failed"] and args.max_error_rate is None:
        gate_failures.append(
            "request failures occurred; set an explicit error-rate gate if allowed"
        )

    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target": args.target,
        "method": "iplms.ai.vision.v1.VisionService/RecognizePlate",
        "image_sha256": hashlib.sha256(image_bytes).hexdigest(),
        "image_bytes": len(image_bytes),
        "image_source": source_description,
        "lane_id": args.lane_id,
        "classify_vehicle": args.classify_vehicle,
        "requests": args.requests,
        "concurrency": args.concurrency,
        "warmup": warmup_samples,
        "summary": summary,
        "gate_failures": gate_failures,
        "samples": samples,
        "pii_warning": (
            "plate numbers and inference outputs may be personal data; "
            "report is gitignored"
        ),
    }
    report_path = args.report or _default_report_path()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"report": str(report_path.resolve()), **summary}, indent=2))
    channel.close()
    return 1 if gate_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
