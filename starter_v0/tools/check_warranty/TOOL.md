---
name: check_warranty
track: bonus
kind: local_inventory
provider: mock_warranty_registry
requires_env: []
inputs: [asset_id, as_of_date]
outputs: [asset_id, model, status, is_active, tier, provider, start_date, end_date, as_of_date, on_site_service, rma_eligible, accidental_damage, source]
side_effect: false
---
# check_warranty

## 1. Description
Tra cứu hợp đồng và trạng thái bảo hành phần cứng của thiết bị công ty (active / expired, gói dịch vụ, hạn bảo hành, tính đủ điều kiện RMA/đổi trả linh kiện tại chỗ) từ cơ sở dữ liệu giả lập nội bộ.

Chức năng này nằm ngoài luồng cơ bản (basic flow trước v0), bổ sung nghiệp vụ quản lý tài sản và hỗ trợ quyết định sửa chữa/thay thế phần cứng.

## 2. Parameter Contract
- `asset_id` (string, required): Mã tài sản công ty hợp lệ (định dạng `LT-xxx`, `DT-xxx`, `MB-xxx`, `PR-xxx`, `RM-xxx`).
- `as_of_date` (string, optional): Ngày mốc đối chiếu bảo hành theo `YYYY-MM-DD`. Khi bỏ trống, tool dùng ngày snapshot trong dữ liệu giả lập.

## 3. Output Contract
Trả về đối tượng JSON với các trường:
- `tool`: `"check_warranty"`
- `asset_id`: Mã tài sản đã chuẩn hóa viết hoa.
- `model`: Tên model thiết bị.
- `status`: `"not_started"`, `"active"` hoặc `"expired"`.
- `is_active`: boolean (`true` nếu còn hạn, `false` nếu hết hạn).
- `tier`: Gói dịch vụ bảo hành (ví dụ: Premier Support, ProSupport Plus).
- `provider`: Nhà cung cấp dịch vụ bảo hành.
- `start_date`: Ngày bắt đầu hiệu lực (`YYYY-MM-DD`).
- `end_date`: Ngày kết thúc hiệu lực (`YYYY-MM-DD`).
- `as_of_date`: Ngày đối chiếu.
- `on_site_service`: boolean (hỗ trợ kỹ thuật tại chỗ).
- `rma_eligible`: boolean (đủ điều kiện đổi mới linh kiện/RMA).
- `accidental_damage`: boolean (bảo hiểm rơi vỡ/hư hỏng bất ngờ).

Trường hợp lỗi:
- Thiếu `asset_id`: `{"tool": "check_warranty", "error": "missing_asset_id"}`
- Sai định dạng: `{"tool": "check_warranty", "asset_id": "...", "error": "invalid_asset_id_format"}`
- Không tìm thấy tài sản: `{"tool": "check_warranty", "asset_id": "...", "error": "warranty_not_found"}`
- Ngày đối chiếu sai định dạng: `{"tool": "check_warranty", "asset_id": "...", "error": "invalid_as_of_date"}`

## 4. Safety & Boundary Guardrails
- Hoàn toàn cục bộ và tất định (deterministic local mock data), không gọi network ngoài.
- Không nhận hoặc lưu trữ dữ liệu nhạy cảm (mật khẩu, token, OTP).
- Không tự suy diễn hay đoán `asset_id`; yêu cầu `clarify` nếu người dùng chưa cung cấp mã tài sản.
