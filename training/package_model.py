"""Mốc CLI: đóng gói weight, manifest, metrics, lock và checksum."""
try:
    from training.workflow_status import run_planned_step
except ModuleNotFoundError:
    from workflow_status import run_planned_step


if __name__ == "__main__":
    run_planned_step("package_model", "Build an immutable candidate model package")
