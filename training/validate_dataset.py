"""Mốc CLI: kiểm schema, checksum, class balance, duplicate và group leakage."""
try:
    from training.workflow_status import run_planned_step
except ModuleNotFoundError:
    from workflow_status import run_planned_step


if __name__ == "__main__":
    run_planned_step("validate_dataset", "Validate frozen dataset before any training run")
