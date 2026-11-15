# Metric contract (khai báo bắt buộc — chốt ở phút 30, trước khi chạy eval)

> Các metric chuẩn đã được cài trong `src/metrics/tracks.py`. File này là nơi nhóm **cam kết** cách dùng chúng.
> Không đổi testset, threshold hay trọng số sau khi đã thấy kết quả eval.

| Mục | Khai báo của nhóm G07 |
|---|---|
| Track | **T02 · Raw QC Triage (Ảnh mờ, lóa và thiếu sáng)** |
| Primary metric (tên đúng như evaluator in ra) | `Defect Recall@B` |
| Tăng tốt hay giảm tốt? | `higher` (càng cao càng tốt) |
| Đơn vị đánh giá (image / region / pair / release / batch / case …) | `image` (toàn ảnh, N=96 images tổng, 40 images trên eval split) |
| Công thức + numerator / denominator | $\text{Recall@B} = \frac{\text{Số ảnh lỗi thật (GT defect) nằm trong Top-B}}{\text{Tổng số ảnh lỗi thật trong tập eval}}$ |
| Cách ghép prediction ↔ GT (IoU? id? tolerance?) | Khớp chính xác theo `image_id` |
| Candidate pool cố định | 40 ảnh trên split `eval` (từ 10 cảnh độc lập) |
| Review budget B / K | $B = 20$ ảnh |
| Seed | `42` |
| Threshold policy (chọn trên dev như thế nào) | Chuẩn hóa theo camera (`cam_A` vs `cam_B`) và ánh sáng (`day`, `dusk`, `night`) trên tập `dev` (56 ảnh); đóng băng threshold trước khi chạy eval |
| Eval split (không dùng để tune) | `eval` |
| Chỉ số lỗi xấu (miss / false alarm / false reject) | `False alarm in top-B` = Số ảnh sạch (clean) bị xếp nhầm vào Top-B / Tổng số ảnh sạch |
| Slices sẽ báo cáo (≥2) | 1. Slice theo điều kiện ánh sáng (`light`: day, dusk, night)<br>2. Slice theo loại lỗi (`defect_type`: blur, dark, glare, compression) |
| Cách báo độ bất định khi N nhỏ (Wilson CI / bootstrap) | Wilson score 95% confidence interval cho Recall@B và False Alarm rate |
| Ngày giờ chốt + người chốt | 15/11/2026 11:15 GMT+7 — Hoàng Bá Đạt (Lead & Reviewer nhóm G07) |

*Ghi chú cam kết:* Không thay đổi metric hay sửa testset để làm đẹp số liệu. Nếu baseline = 0 thì ghi rõ "baseline = 0" thay vì phần trăm cải thiện ảo.
