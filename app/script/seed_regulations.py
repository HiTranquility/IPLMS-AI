"""Script seed dữ liệu tri thức quy chế bãi xe & biểu phí vào pgvector / local fallback.
Phục vụ RAG Copilot trả lời câu hỏi và phân xử khiếu nại tranh chấp vé đỗ xe.
"""
import os
import json
import asyncio
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

# Danh mục các quy chế, biểu phí mẫu chuẩn cho bãi xe thông minh
SAMPLE_KNOWLEDGE_CHUNKS = [
    {
        "category": "tariff",
        "title": "Biểu Phí Gửi Xe Ô Tô Bậc Thang (Khu vực Trung tâm)",
        "content": (
            "Biểu phí gửi xe ô tô tại các bãi xe trung tâm (Landmark 81, Vincom Đồng Khởi):\n"
            "- 2 giờ đầu tiên: 35.000 VNĐ / giờ.\n"
            "- Từ giờ thứ 3 đến giờ thứ 5: 45.000 VNĐ / giờ.\n"
            "- Từ giờ thứ 6 trở đi: Áp dụng mức phí lũy tiến 55.000 VNĐ / giờ.\n"
            "- Khung giờ ban đêm (từ 22:00 đến 06:00 sáng hôm sau): Phụ thu thêm 50.000 VNĐ / lượt qua đêm.\n"
            "- Miễn phí 15 phút đầu tiên đối với các lượt xe vào trả khách (Drop-off)."
        ),
        "source": "Bieu_phi_do_xe_o_to_2026.pdf",
        "parking_lot_id": "lot_landmark_81"
    },
    {
        "category": "tariff",
        "title": "Biểu Phí Gửi Xe Máy & Xe Đạp Điện",
        "content": (
            "Biểu phí gửi xe máy tại toàn bộ hệ thống bãi xe IPLMS:\n"
            "- Khung giờ ban ngày (06:00 - 22:00): 6.000 VNĐ / lượt (tối đa 4 tiếng), mỗi 4 tiếng tiếp theo cộng 4.000 VNĐ.\n"
            "- Khung giờ ban đêm (22:00 - 06:00): 15.000 VNĐ / lượt qua đêm.\n"
            "- Gói gửi xe tháng (Member VIP): 180.000 VNĐ / tháng (được cố định ô đỗ và tự động mở barrier bằng ANPR)."
        ),
        "source": "Quy_dinh_xe_may_2026.pdf",
        "parking_lot_id": None
    },
    {
        "category": "regulation",
        "title": "Quy Chế Xử Lý Tranh Chấp & Hoàn Tiền Khiếu Nại (Dispute Policy)",
        "content": (
            "Điều 5 - Quy trình xử lý khiếu nại và hoàn phí:\n"
            "1. Trường hợp cảm biến barie hoặc hệ thống quét biển số (ANPR) gặp sự cố kỹ thuật dẫn đến chậm trễ lúc ra cổng > 10 phút, hệ thống tự động trừ thời gian trễ này khỏi tổng thời gian tính phí.\n"
            "2. Khách hàng có quyền tạo yêu cầu Khiếu nại (Dispute Ticket) trên ứng dụng trong vòng 48 giờ kể từ khi kết thúc phiên gửi.\n"
            "3. Trợ lý AI Copilot sẽ đối chiếu video log và thời gian thực để đề xuất hoàn tiền 100% phần phí chênh lệch do lỗi hệ thống vào ví IPLMS Wallet trong vòng 15 phút."
        ),
        "source": "Quy_che_xu_ly_khieu_nai_dieu_5.pdf",
        "parking_lot_id": None
    },
    {
        "category": "fine_policy",
        "title": "Chính Sách Xử Phạt Vi Phạm Đỗ Sai Vị Trí & Quá Giờ",
        "content": (
            "Điều 8 - Xử phạt vi phạm nội quy bãi đỗ xe:\n"
            "- Đỗ sai ô đã đặt trước (sai slot ID được chỉ định): Phạt cảnh cáo lần đầu, tái phạm phạt 50.000 VNĐ.\n"
            "- Chiếm dụng ô sạc xe điện (EV Charging Slot) mà không sạc hoặc đã sạc đầy quá 30 phút: Phụ thu 20.000 VNĐ / 30 phút quá giờ.\n"
            "- Gửi xe quá hạn hợp đồng tháng hoặc quá 72 giờ không thông báo: Xe sẽ bị khóa bánh tại chỗ, phí mở khóa là 200.000 VNĐ kèm tiền gửi lũy tiến."
        ),
        "source": "Noi_quy_va_che_tai_bai_xe.pdf",
        "parking_lot_id": None
    },
    {
        "category": "ev_charging",
        "title": "Chính Sách Trạm Sạc Xe Điện (EV Charging Station)",
        "content": (
            "Quy định sử dụng trụ sạc AC/DC tại bãi xe:\n"
            "- Đơn giá sạc điện: 3.850 VNĐ / kWh (chưa bao gồm VAT).\n"
            "- Phí đỗ xe trong thời gian đang sạc (dưới 2 giờ): Giảm 50% so với biểu phí gửi xe thông thường.\n"
            "- Sau khi sạc đầy (pin đạt 100%), hệ thống gửi thông báo qua App. Chủ xe có 30 phút ân hạn để di chuyển xe sang ô đỗ tiêu chuẩn."
        ),
        "source": "Huong_dan_tram_sac_ev.pdf",
        "parking_lot_id": "lot_vincom_center"
    },
    # ── Hai mục dưới đây mô tả ĐÚNG luật đang chạy trong code, không phải luật
    # ước lệ. Nguồn sự thật: `backend/src/modules/Parking/services/shared/
    # overstay-penalty.policy.ts` (công thức + trần nền tảng) và
    # `.../operation-settings.policy.ts` (khung chủ bãi được đặt).
    #
    # [MUST] Sửa hai file đó ⇒ sửa luôn hai mục này. Copilot trả lời khác con số
    # hệ thống thực thu là cách nhanh nhất để đẻ ra một vụ khiếu nại mà chính
    # trợ lý AI đã hứa sai.
    {
        "category": "fine_policy",
        "title": "Phụ Phí Quá Giờ (Overstay) — Cách Tính Chính Thức",
        "content": (
            "Điều 9 - Phụ phí khi xe ở quá giờ đã đặt:\n"
            "1. Ân hạn: quá giờ trong khoảng ân hạn của bãi thì KHÔNG có phụ phí. Mặc định 15 phút; mỗi bãi tự đặt trong khoảng 0-60 phút.\n"
            "2. Quá ân hạn: tính phụ phí theo GIỜ BẮT ĐẦU (quá 10 phút vẫn tính tròn 1 giờ). Mặc định 5.000 VNĐ/giờ, trần nền tảng là 20.000 VNĐ/giờ.\n"
            "3. Phụ phí này CỘNG THÊM vào tiền giờ thực đỗ, không thay thế tiền giờ.\n"
            "4. Có trần cho mỗi lượt: mặc định 50.000 VNĐ, tối đa 100.000 VNĐ tuỳ bãi.\n"
            "5. Trường hợp khách vãng lai chiếm ô đã bán vé tháng/flex của người khác, phụ phí bị nhân tối đa 3 lần vì đã đẩy chủ ô hợp lệ ra ngoài.\n"
            "6. Mức của từng bãi được công khai cho khách TRƯỚC khi đặt (màn hình chi tiết bãi và trên vé), không phải tới lúc ra cổng mới biết."
        ),
        "source": "Chinh_sach_phu_phi_qua_gio_dieu_9.pdf",
        "parking_lot_id": None
    },
    {
        "category": "regulation",
        "title": "Khung Quy Định Vận Hành Mỗi Bãi Được Tự Đặt",
        "content": (
            "Điều 10 - Phạm vi chủ bãi được tự quyết:\n"
            "- Chủ bãi đặt riêng cho bãi mình: thời gian ân hạn quá giờ, phụ phí quá giờ mỗi giờ, trần phụ phí mỗi lượt, ân hạn và mức phạt nhân viên vào ca trễ.\n"
            "- Mọi tham số đều bị kẹp trong khung cứng của nền tảng. Đặt vượt khung thì hệ thống tự kéo về giá trị hợp lệ gần nhất chứ không áp con số vượt trần.\n"
            "- Bãi không đặt gì riêng thì chạy theo mặc định nền tảng: ân hạn 15 phút, phụ phí 5.000 VNĐ/giờ, trần 50.000 VNĐ/lượt.\n"
            "- Thay đổi quy định chỉ áp dụng cho lượt đặt MỚI. Lượt đã đặt trước đó giữ nguyên điều kiện tại thời điểm đặt.\n"
            "- Khách có quyền yêu cầu đối chiếu mức phí đã công bố lúc đặt với mức bị thu lúc ra cổng; lệch nhau thì xử theo Điều 5 (khiếu nại & hoàn tiền)."
        ),
        "source": "Quy_dinh_van_hanh_bai_xe_dieu_10.pdf",
        "parking_lot_id": None
    }
]

async def _ingest_demo_data() -> None:
    """Embed demo data through the same production ingestion pipeline.

    The generated source name says ``demo`` explicitly. The previous script
    inserted NULL embeddings while citing PDF files that did not exist, which
    made retrieval both unusable and misleading.
    """
    from app.core.knowledge.dtos.knowledge_dto import IngestDocumentCommand
    from app.core.knowledge.services import ingestion_service

    for index, chunk in enumerate(SAMPLE_KNOWLEDGE_CHUNKS, start=1):
        source = f"demo_{index:02d}_{chunk['category']}.md"
        body = f"# {chunk['title']}\n\n{chunk['content']}\n"
        result = await ingestion_service.ingest(
            IngestDocumentCommand(
                file_data=body.encode("utf-8"),
                file_name=source,
                parking_lot_id=chunk.get("parking_lot_id"),
                category=chunk["category"],
                uploaded_by="seed-script",
                # Deterministic per source + tenant: re-running the seed is a
                # safe replace, not an ever-growing set of duplicate chunks.
                document_id=uuid5(
                    NAMESPACE_URL,
                    f"iplms-demo:{source}:{chunk.get('parking_lot_id') or 'global'}",
                ),
            )
        )
        if result.status.value != "SUCCESS":
            raise RuntimeError(f"Không nạp được {source}: {result.message}")
        print(f"[OK] Ingested {source}: {result.chunk_count} chunks")


def seed_knowledge():
    ai_dir = Path(__file__).resolve().parent.parent.parent
    data_dir = ai_dir / "data" / "knowledge"
    data_dir.mkdir(parents=True, exist_ok=True)

    # 1. Xuất file JSON cục bộ làm Knowledge Base chuẩn
    output_file = data_dir / "regulations_seed.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(SAMPLE_KNOWLEDGE_CHUNKS, f, ensure_ascii=False, indent=2)

    print(f"[OK] Saved {len(SAMPLE_KNOWLEDGE_CHUNKS)} knowledge chunks to: {output_file}")

    # 2. Chỉ nạp demo khi đã cấu hình cả DB và OpenAI. Không còn đường ghi
    # embedding=NULL: hoặc nạp trọn vẹn, hoặc không ghi gì.
    db_url = os.getenv("AI_DATABASE_URL", "")
    api_key = os.getenv("AI_LLM_API_KEY", "")
    if db_url and api_key:
        asyncio.run(_ingest_demo_data())
    else:
        print("[INFO] Chỉ xuất JSON; cần AI_DATABASE_URL + AI_LLM_API_KEY để nạp demo.")

if __name__ == "__main__":
    seed_knowledge()
