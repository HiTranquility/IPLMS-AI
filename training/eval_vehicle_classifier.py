"""Mốc CLI: đánh giá classifier trên test-golden không dùng để tune."""
try:
    from training.workflow_status import run_planned_step
except ModuleNotFoundError:
    from workflow_status import run_planned_step


if __name__ == "__main__":
    run_planned_step("eval_vehicle_classifier", "Evaluate per-class metrics and latency")
