"""Câu Copilot trả cho người dùng (ADR-0005).

Eval nhận ra câu từ chối bằng `knowledge_eval/engines/grader.py::is_refusal`;
`test/test_knowledge_eval.py` trói hai bên — sửa câu ở đây thì sửa marker ở đó.
"""

NO_CONTEXT_ANSWER = (
    "Mình chưa tìm thấy thông tin đủ liên quan trong kho tri thức để trả lời "
    "chắc chắn. Bạn hãy chọn đúng bãi xe hoặc nhờ chủ bãi bổ sung quy chế."
)

GUARD_NOTICE = (
    "Mình dừng câu trả lời vì nó có nội dung không khớp tài liệu của bãi. "
    "Bạn xem trực tiếp quy chế của bãi hoặc hỏi nhân viên giúp mình nhé."
)
