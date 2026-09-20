"""Mốc CLI: publish candidate theo version bất biến lên artifact storage."""
try:
    from training.workflow_status import run_planned_step
except ModuleNotFoundError:
    from workflow_status import run_planned_step


if __name__ == "__main__":
    run_planned_step("publish_model", "Upload a verified candidate without changing accepted alias")
