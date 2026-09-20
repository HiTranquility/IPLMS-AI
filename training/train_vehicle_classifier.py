"""Mốc CLI chuẩn cho train classifier local hoặc Colab."""
try:
    from training.workflow_status import run_planned_step
except ModuleNotFoundError:
    from workflow_status import run_planned_step


if __name__ == "__main__":
    run_planned_step("train_vehicle_classifier", "Train the four-class vehicle classifier")
