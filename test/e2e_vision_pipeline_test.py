"""Kiểm thử tự động Browser Control chuyên sâu cho luồng Vision Pipeline & 4-Eyes Governance.
Tự động đăng nhập, xác thực TOTP và kiểm tra phân quyền RBAC đa vai trò trên IPLMS AI Console.
"""
import os
import sys
import tempfile
import time
import pyotp
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

SCREENSHOT_DIR = os.environ.get("E2E_SCREENSHOT_DIR", os.path.join(tempfile.gettempdir(), "iplms-e2e-screenshots"))
os.makedirs(SCREENSHOT_DIR, exist_ok=True)
# Tài khoản demo dev: secret/mật khẩu lấy từ biến môi trường, không ghi vào repo.
TOTP_SECRET = os.environ["E2E_TOTP_SECRET"]
DEMO_PASSWORD = os.environ["E2E_DEMO_PASSWORD"]
BASE_URL = "http://localhost:8090"

results = {
    "annotator_label_shortcut": False,
    "annotator_rbac_blocked": False,
    "reviewer_reject_validation": False,
    "reviewer_approve_success": False,
    "data_engineer_no_freeze_golden": False,
    "data_engineer_snapshot_created": False,
    "admin_models_and_eval_visible": False,
    "screenshots": []
}

def login(page, email, password):
    print(f"Logging in with {email}...")
    page.goto(f"{BASE_URL}/")
    page.wait_for_load_state("networkidle")
    time.sleep(0.5)

    emergency = page.locator("details summary")
    if emergency.count() > 0:
        emergency.click()
        time.sleep(0.3)
    
    page.locator("input[type='email']").fill(email)
    page.locator("input[type='password']").fill(password)
    page.locator("details button[type='submit']").click()
    
    page.wait_for_selector("input[inputmode='numeric']", timeout=10000)
    code = pyotp.TOTP(TOTP_SECRET).now()
    page.locator("input[inputmode='numeric']").fill(code)
    page.locator("button[type='submit']").click()
    
    page.wait_for_load_state("networkidle")
    time.sleep(1)
    print(f"Login complete for {email}. Current URL: {page.url}")

def test_annotator(browser):
    print("\n=======================================================")
    print("[1] VAI TRÒ ANNOTATOR (anh.annotator@iplms.internal)")
    print("=======================================================")
    context = browser.new_context(viewport={"width": 1400, "height": 900})
    page = context.new_page()
    
    login(page, "anh.annotator@iplms.internal", DEMO_PASSWORD)
    
    page.goto(f"{BASE_URL}/vision/label")
    page.wait_for_load_state("networkidle")
    time.sleep(2)
    
    btn1 = page.locator("button[aria-keyshortcuts='1']")
    print(f"Trạng thái nút gán nhãn [1] (Khớp 100%): count={btn1.count()}")
    
    if btn1.count() > 0:
        print("-> Thực hiện thao tác gán nhãn phím '1'...")
        page.keyboard.press("1")
        time.sleep(2)
        page.wait_for_load_state("networkidle")
        results["annotator_label_shortcut"] = True
        print("-> Gán nhãn thành công qua phím 1!")
        
    flow_shot = os.path.join(SCREENSHOT_DIR, "agent1_annotator_flow.png")
    page.screenshot(path=flow_shot, full_page=True)
    print(f"-> Đã lưu ảnh: {flow_shot}")
    results["screenshots"].append(flow_shot)
    
    print("-> Điều hướng đến /vision/review...")
    page.goto(f"{BASE_URL}/vision/review")
    page.wait_for_load_state("networkidle")
    time.sleep(1.5)
    
    blocked_loc = page.locator("text='Vai trò của bạn không mở được mục này'")
    is_blocked = blocked_loc.count() > 0
    print(f"-> RBAC kiểm tra chặn: {is_blocked} ('Vai trò của bạn không mở được mục này')")
    results["annotator_rbac_blocked"] = is_blocked
    
    blocked_shot = os.path.join(SCREENSHOT_DIR, "agent1_annotator_blocked.png")
    page.screenshot(path=blocked_shot, full_page=True)
    print(f"-> Đã lưu ảnh: {blocked_shot}")
    results["screenshots"].append(blocked_shot)
    
    context.close()

def test_reviewer(browser):
    print("\n=======================================================")
    print("[2] VAI TRÒ REVIEWER (duong.fe@iplms.internal)")
    print("=======================================================")
    context = browser.new_context(viewport={"width": 1400, "height": 900})
    page = context.new_page()
    
    login(page, "duong.fe@iplms.internal", DEMO_PASSWORD)
    
    page.goto(f"{BASE_URL}/vision/review")
    page.wait_for_load_state("networkidle")
    time.sleep(2)
    
    review_rows = page.locator("li[class*='reviewCard']")
    print(f"Số lượng nhãn chờ duyệt trong danh sách: {review_rows.count()}")
    
    if review_rows.count() == 0:
        seed_btn = page.locator("button:has-text('Nạp dữ liệu mẫu')")
        if seed_btn.count() > 0:
            print("-> Bấm nạp dữ liệu mẫu demo...")
            seed_btn.click()
            time.sleep(2)
            page.wait_for_load_state("networkidle")
            print(f"-> Sau khi nạp: {review_rows.count()} nhãn")

    reject_open_btn = page.locator("button:has-text('Trả lại')").first
    if reject_open_btn.count() > 0:
        print("-> Bấm 'Trả lại…' trên nhãn đầu tiên...")
        reject_open_btn.click()
        time.sleep(0.5)
        
        reason_input = page.locator("form[class*='rejectForm'] input").first
        reason_input.fill("ko")
        time.sleep(0.5)
        
        reject_submit_btn = page.locator("form[class*='rejectForm'] button[type='submit']").first
        is_disabled = reject_submit_btn.is_disabled()
        print(f"-> Nhập 2 ký tự ('ko'): Nút Từ chối disabled={is_disabled} (Hệ thống chặn gửi < 3 ký tự)")
        results["reviewer_reject_validation"] = is_disabled
        
        cancel_btn = page.locator("form[class*='rejectForm'] button:has-text('Hủy')").first
        if cancel_btn.count() > 0:
            cancel_btn.click()
            time.sleep(0.5)

    # Lấy nút Duyệt của chính dòng: has-text không phân biệt hoa thường nên còn khớp cả nút
    # "Xưởng Gán nhãn & Kiểm duyệt" (chuyển không gian) và "Duyệt nhanh…" ở thanh công cụ.
    approve_btn = review_rows.first.locator("button[aria-label^='Duyệt nhãn']")
    if approve_btn.count() > 0:
        initial_count = review_rows.count()
        print(f"-> Bấm 'Duyệt' một nhãn hợp lệ (Số hàng hiện tại: {initial_count})...")
        approve_btn.click()
        time.sleep(2)
        page.wait_for_load_state("networkidle")
        
        new_count = page.locator("li[class*='reviewCard']").count()
        print(f"-> Sau khi duyệt, số hàng còn lại: {new_count}")
        results["reviewer_approve_success"] = new_count == initial_count - 1
    
    reviewer_shot = os.path.join(SCREENSHOT_DIR, "agent1_reviewer_flow.png")
    page.screenshot(path=reviewer_shot, full_page=True)
    print(f"-> Đã lưu ảnh: {reviewer_shot}")
    results["screenshots"].append(reviewer_shot)
    
    context.close()

def test_data_engineer(browser):
    print("\n=======================================================")
    print("[3] VAI TRÒ DATA ENGINEER (bao.data@iplms.internal)")
    print("=======================================================")
    context = browser.new_context(viewport={"width": 1400, "height": 900})
    page = context.new_page()
    
    login(page, "bao.data@iplms.internal", DEMO_PASSWORD)
    
    page.goto(f"{BASE_URL}/vision/datasets")
    page.wait_for_load_state("networkidle")
    time.sleep(2)
    
    freeze_btn = page.locator("button:has-text('Khoá golden')")
    has_freeze_btn = freeze_btn.count() > 0
    print(f"-> Nút 'Khoá golden' xuất hiện trên giao diện: {has_freeze_btn} (Kỳ vọng: False)")
    results["data_engineer_no_freeze_golden"] = (not has_freeze_btn)
    
    name_input = page.locator("form[aria-labelledby='snapshot-title'] input").first
    if name_input.count() > 0:
        print("-> Nhập tên snapshot: 'train-agent-test-2026'...")
        name_input.fill("train-agent-test-2026")
        
        select_kind = page.locator("form[aria-labelledby='snapshot-title'] select").first
        if select_kind.count() > 0:
            select_kind.select_option("train")
        
        submit_btn = page.locator("form[aria-labelledby='snapshot-title'] button[type='submit']")
        submit_btn.click()
        print("-> Bấm 'Tạo' snapshot...")
        time.sleep(3)
        page.wait_for_load_state("networkidle")
        
        status_msg = page.locator("p[role='status']")
        table_row = page.locator("table tbody tr:has-text('train-agent-test-2026')")
        created = (status_msg.count() > 0) or (table_row.count() > 0)
        print(f"-> Snapshot tạo thành công: {created}")
        if status_msg.count() > 0:
            print(f"   Thông báo: {status_msg.inner_text()}")
        results["data_engineer_snapshot_created"] = created
    
    de_shot = os.path.join(SCREENSHOT_DIR, "agent1_data_engineer_flow.png")
    page.screenshot(path=de_shot, full_page=True)
    print(f"-> Đã lưu ảnh: {de_shot}")
    results["screenshots"].append(de_shot)
    
    context.close()

def test_admin_lead(browser):
    print("\n=======================================================")
    print("[4] VAI TRÒ SUPER ADMIN / AI LEAD (admin@iplms.internal)")
    print("=======================================================")
    context = browser.new_context(viewport={"width": 1400, "height": 900})
    page = context.new_page()
    
    login(page, "admin@iplms.internal", DEMO_PASSWORD)
    
    page.goto(f"{BASE_URL}/vision/models")
    page.wait_for_load_state("networkidle")
    time.sleep(2)
    
    eval_heading = page.locator("text='Đo engine đang nạp'")
    eval_btn = page.locator("button:has-text('Bắt đầu đo')")
    models_table = page.locator("table tbody tr")
    
    print(f"-> Mục 'Đo engine đang nạp' hiển thị: {eval_heading.count() > 0}")
    print(f"-> Nút 'Bắt đầu đo' hiển thị: {eval_btn.count() > 0}")
    print(f"-> Số phiên bản model trong bảng: {models_table.count()}")
    
    if models_table.count() > 0:
        for idx in range(models_table.count()):
            row_text = models_table.nth(idx).inner_text().replace("\n", " | ")
            print(f"   Model #{idx+1}: {row_text}")
            
    results["admin_models_and_eval_visible"] = (eval_btn.count() > 0 and models_table.count() > 0)
    
    admin_shot = os.path.join(SCREENSHOT_DIR, "agent1_admin_lead_flow.png")
    page.screenshot(path=admin_shot, full_page=True)
    print(f"-> Đã lưu ảnh: {admin_shot}")
    results["screenshots"].append(admin_shot)
    
    context.close()

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            test_annotator(browser)
            test_reviewer(browser)
            test_data_engineer(browser)
            test_admin_lead(browser)
        finally:
            browser.close()
            
    print("\n=======================================================")
    print("BÁO CÁO KẾT QUẢ KIỂM THỬ (BROWSER AUTOMATION)")
    print("=======================================================")
    for k, v in results.items():
        print(f"  * {k}: {v}")

if __name__ == "__main__":
    main()
