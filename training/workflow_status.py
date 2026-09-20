"""CLI dùng chung cho các bước training đã được đánh dấu nhưng chưa triển khai."""
import argparse


def run_planned_step(step: str, purpose: str) -> None:
    parser = argparse.ArgumentParser(description=purpose)
    parser.add_argument(
        "--status",
        action="store_true",
        help="In trạng thái scaffold và đường dẫn runbook.",
    )
    args = parser.parse_args()
    if args.status:
        print(f"{step}: PLANNED")
        print(purpose)
        print("Runbook: docs/guides/06-google-colab-training-runbook.md")
        return
    parser.error("Bước này mới là scaffold; dùng --status để xem mốc triển khai")
