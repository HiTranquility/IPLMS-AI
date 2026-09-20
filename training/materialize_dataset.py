"""Mốc CLI: tải snapshot đã khóa từ object storage về workspace local."""
try:
    from training.workflow_status import run_planned_step
except ModuleNotFoundError:
    from workflow_status import run_planned_step


if __name__ == "__main__":
    run_planned_step("materialize_dataset", "Private manifest -> model/dataset/<task>/materialized")
