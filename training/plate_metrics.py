"""Re-export — logic chấm biển số nằm ở `app/core/dataset/engines/plate_metrics.py`.

Chuyển vào `app/` (ISSUE-013) vì image Docker của ai chỉ COPY `ai/app`, còn
`training/` thì không: RPC đo ANPR trên snapshot cần đúng logic này khi chạy
trong container. Giữ file này để `training/eval_plates.py` và test cũ không đổi.
"""
from app.core.dataset.engines.plate_metrics import *  # noqa: F401,F403
from app.core.dataset.engines.plate_metrics import (  # noqa: F401
    aggregate,
    char_error_rate,
    group_by_tag,
    levenshtein,
    normalize_relaxed,
    normalize_strict,
    percentile,
    score_one,
)
