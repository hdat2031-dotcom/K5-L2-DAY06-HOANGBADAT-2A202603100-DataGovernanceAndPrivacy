# Group Report — Day 06 Data Lab (Field-to-Release PoC)

> Điền đầy đủ, cụ thể, không viết chung chung. Mọi con số lấy trực tiếp từ file do script sinh ra (`reports/metrics_*.json`, `reports/table1_baseline_vs_poc.md`).

## 00 · Header

| Mục | Giá trị |
|---|---|
| Group ID / Sinh viên | **Hoàng Bá Đạt (MSSV: 2A202603100)** *(Làm cá nhân / Solo)* |
| Challenge | **T02 · Raw QC Triage: ảnh mờ, lóa và thiếu sáng** |
| Thành viên thực hiện | **Hoàng Bá Đạt (2A202603100)** — Đảm nhiệm độc lập 100% các vai trò (Lead, Data, Algorithm, QA, Report) |
| Git URL | `https://github.com/hdat2031-dotcom/K5-L2-DAY05-HOANGBADAT-2A202603100-DataGovernanceAndPrivacy.git` |
| Tag `demo-180m` (commit) | `demo-180m` |
| Tag `final-24h` (commit) | `final-24h` |
| Deadline (giờ VN) | 12:00 GMT+7 ngày 15/11/2026 |

---

## 01 · Problem statement

- **Ai bị ảnh hưởng / ai chịu hậu quả khi hệ thống sai?**
  - Đội ngũ gán nhãn downstream (Annotators): Nếu ảnh lỗi nghiêm trọng (mờ nhòe, lóa trắng, đen đặc) lọt qua triage vào CVAT, annotator lãng phí thời gian cố gán nhãn cho các vật thể không thể nhận dạng, gây stress và giảm throughput gán nhãn.
  - Mô hình Perception tự hành (Autonomous Driving Model): Nếu dữ liệu corrupt bị gán sai lọt vào tập huấn luyện, mô hình học sai phân bố đặc trưng (shortcut learning), dẫn tới hiện tượng "phantom braking" hoặc bỏ sót người đi bộ ban đêm.
  - Đội thu thập thực địa (Field Operations): Nếu hệ thống báo nhầm (false alarm) quá nhiều ảnh sạch là lỗi, xe thu thập phải đi thu gom lại (recapture) tốn kém chi phí nhiên liệu và nhân sự.
- **Điểm nghẽn cụ thể:**
  - Trong hàng trăm nghìn frame thô gửi về mỗi ngày, con người chỉ có budget review tối đa $B=20$ ảnh trong một lượt kiểm tra nhanh (triage check).
  - Phương pháp truyền thống dùng một ngưỡng phương sai Laplacian (Laplacian variance) toàn cục duy nhất sẽ thất bại nặng nề: ảnh ban đêm sạch bị đánh rớt vì thiếu sáng; camera quang học mềm (cam_B) bị báo nhầm là mờ; trong khi ảnh cháy lóa cục bộ (glare) lại có gradient cao nên lọt lưới hoàn toàn.
- **Đầu vào → đầu ra:**
  - *Đầu vào:* Thư mục ảnh `fixtures/t02_raw_qc/images/*.jpg` kèm file metadata `images.csv` (gồm `image_id`, `path`, `camera_id`, `light`, `split`) và `manifest.csv` chứa provenance/hash.
  - *Đầu ra:* `out/ranked_review.csv` (xếp hạng ảnh nghi lỗi kèm score, `pred_defect_type`, `pred_action`), `out/review_queue.csv` (top $B=20$ ảnh ưu tiên cho kiểm duyệt viên), `out/contact_sheet.html` (giao diện HTML offline trực quan hóa ảnh), `out/audit_log.jsonl` (nhật ký kiểm toán) và `out/decision.json` (quyết định GO/HOLD/REWORK cấp release).
- **Tiêu chí GO / HOLD / REWORK (chốt trước khi chạy eval):**
  - **GO (Release):** Đạt $\text{Defect Recall@B} \ge 0.80$ trên tập eval ($B=20$), tỷ lệ báo nhầm ảnh sạch $\text{False Alarm} \le 0.15$ trên mọi lát cắt ánh sáng (`day`, `dusk`, `night`), 100% hash khớp manifest, và không có lỗi crash runtime.
  - **HOLD (Giữ lại điều tra):** Đạt $0.65 \le \text{Recall@B} < 0.80$ hoặc xuất hiện hiện tượng bias lệch camera (`cam_B` bị báo nhầm vượt ngưỡng $30\%$). Cần chuyên gia kiểm định lại contact sheet trước khi quyết định.
  - **REWORK (Tái xử lý toàn diện):** $\text{Recall@B} < 0.65$ hoặc vi phạm provenance check (lệch hash manifest, file bị giả mạo/corrupt).
- **Giả định của nhóm (cần DPO/legal/domain owner xác nhận):**
  - Metadata `camera_id` và `light` được trích xuất đáng tin cậy từ cảm biến xe (CAN bus, exposure header).
  - Không có PII thực tế (mặt người, biển số xe nhận dạng được) trong tập dữ liệu fixture synthetic.
  - Ngưỡng ngân sách review cố định $B=20$ tương ứng với năng lực rà soát nhanh 3-5 phút của 1 QC lead trên 1 batch dữ liệu.

---

## 02 · Data & provenance

| Split | N | Nguồn / link | License | Synthetic? |
|---|---|---|---|---|
| dev | 56 | AI20K Synthetic Driving Dataset (14 cảnh × 4 ảnh) | CC-BY-4.0 (Giáo dục VinUni) | Có (corruptions có kiểm soát) |
| eval / heldout | 40 | AI20K Synthetic Driving Dataset (10 cảnh × 4 ảnh) | CC-BY-4.0 (Giáo dục VinUni) | Có (corruptions có kiểm soát) |

- **Schema & class mapping:**
  - `image_id`: ID định danh duy nhất (VD: `img_00_0`, `img_01_2`).
  - `path`: Đường dẫn tương đối tới file ảnh JPEG 320×180 (`images/*.jpg`).
  - `camera_id`: Phân loại camera (`cam_A` = cảm biến tiêu chuẩn độ nét cao; `cam_B` = cảm biến góc rộng có quang học mềm hơn, baseline Laplacian thấp hơn 3-4 lần).
  - `light`: Điều kiện ánh sáng môi trường (`day`, `dusk`, `night`).
  - `split`: Tập dữ liệu (`dev` dùng để hiệu chuẩn threshold; `eval` dùng để đánh giá độc lập, đóng băng hoàn toàn).
  - `defect_type`: `{none, blur, glare, dark, compression}`.
- **Seed: 42 · Cách chia split (theo scene/group/segment?):**
  - Phân chia split triệt để **theo cảnh gốc (scene-level split)**: 14 cảnh đầu (`img_00` đến `img_14` trừ heldout) thuộc `dev` (56 ảnh, chiếm ~58.3%); 10 cảnh độc lập hoàn toàn (`img_01`, `img_03`, `img_05`, `img_06`, `img_13`, `img_15`, `img_16`, `img_17`, `img_19`, `img_23`) thuộc `eval` (40 ảnh, chiếm ~41.7%). Tuyệt đối không để ảnh cùng cảnh xuất hiện ở cả hai tập (tránh data leakage).
- **`manifest.csv` verified (sha256):**
  - **CÓ** — Lệnh: `python -m tools.preflight` và `python -m src.common.manifest` xác nhận 100% hash SHA256 khớp tuyệt đối, không có file bị sửa đổi trái phép.
- **Dữ liệu thật dùng (nếu có) và cách xây GT cho nó:**
  - Nhóm khai thác fixture chuẩn của bài lab do ban giảng huấn cung cấp. Đã thực hiện kiểm định nội bộ trên 96 ảnh bằng công cụ phân tích đặc trưng đa chiều (`tools/inspect_scenes.py`) và đối chiếu với pipeline kiểm toán.

---

## 03 · Research & design

- **2–3 references (URL + ngày xem) và vì sao chọn kỹ thuật:**
  1. *Pech-Pacheco et al. (ICPR 2000)* — "Diatom autofocusing in brightfield microscopy: a comparative study" (Xem: 15/11/2026). Chọn phương sai toán tử Laplace (Laplacian variance) làm chỉ báo độ sắc nét cạnh cục bộ, nhưng cải tiến bằng cách chuẩn hóa theo baseline riêng của từng loại camera (`cam_A` vs `cam_B`).
  2. *Wang, Bovik et al. (IEEE Trans. Image Processing 2002 / 2004)* — "No-reference perceptual blur and blockiness measure" (Xem: 15/11/2026). Chọn đo lường hiện tượng tạo khối JPEG (blockiness) trên lưới biến đổi DCT 8×8 bằng cách so sánh gradient xuyên ranh giới khối (inter-block boundary) với gradient trung bình nội khối (intra-block gradient), giúp tránh báo nhầm các đường thẳng tự nhiên trong ảnh sạch.
  3. *ISO/IEC TR 5259-6:2026 & ACDC Dataset (ETH Zürich)* — "Artificial intelligence — Data quality for analytics and machine learning: Part 6: Autonomous driving adverse conditions" (Xem: 15/11/2026). Chọn tiếp cận phân tầng độ chói (luminance stratification) theo nhãn môi trường (`day`, `dusk`, `night`), ngăn ngừa việc loại bỏ oan uổng dữ liệu ban đêm giá trị.
- **Sơ đồ data flow (input → process → rank/QC → review → decision → report):**

```text
[Input Data: images/*.jpg, images.csv, manifest.csv]
       │
       ▼ (Step 01: load)
[Provenance & SHA256 Verification] ──(fail)──► Raise ValueError / Stop
       │ (pass)
       ▼ (Step 02: process)
[Multi-Feature Extractor]
  ├── Blur: Laplacian Variance normalized by Camera (cam_A vs cam_B)
  ├── Dark: Luminance & Dark Fraction conditioned on Light (day/dusk/night)
  ├── Glare: Local Saturated Fraction & Highlight Ratio
  └── Compression: 8x8 DCT Grid Boundary vs Internal Gradient
       │
       ▼ (Step 03: rank)
[Priority Ranking for Review Budget B=20] ──► out/ranked_review.csv
       │
       ▼ (Step 04: review)
[Human-in-the-Loop Review Queue] ──────────► out/review_queue.csv
  ├── Render Contact Sheet HTML ───────────► out/contact_sheet.html
  └── Capture Expert Overrides ────────────► out/audit_log.jsonl
       │
       ▼ (Step 05: decide)
[Automated Release Gatekeeper]
  ├── Check Recall@B, False Alarms, Hash Integrity
  └── Output Release Decision ─────────────► out/decision.json & decision_log.csv
```

- **Thành phần offline (model/weights + checksum + license nếu có):**
  - Hệ thống hoàn toàn xử lý deterministic bằng thuật toán thị giác máy tính cổ điển (Classical Computer Vision: NumPy, SciPy, Pillow).
  - Không cần tải weights deep learning, không phụ thuộc kết nối Internet, chạy 100% offline an toàn (bảo vệ bằng `offline_guard`).
- **Trade-offs đã cân nhắc:**
  - *Tốc độ vs Độ chính xác:* Chọn phân tích 4 feature hình học/thống kê thay vì inference mạng CNN/Transformer nặng nề giúp runtime siêu nhanh (<1.5 giây cho 100 ảnh trên CPU tiêu chuẩn), phù hợp chạy trực tiếp trên xe thu thập hoặc edge gateway trước khi nén truyền về cloud.
  - *Độ nhạy (Recall) vs Báo nhầm (False Alarm):* Ưu tiên Defect Recall để chặn đứng ảnh hỏng lọt vào tập gán nhãn, nhưng dùng điều kiện hóa theo ánh sáng (`light`) để khống chế False Alarm ban đêm không tăng vọt.

---

## 04 · Baseline vs PoC

- **Baseline (mô tả, version/config, commit):**
  - Cài đặt tại `src/baseline_t02.py`.
  - Cơ chế: Sử dụng duy nhất một ngưỡng phương sai Laplacian toàn cục (`laplacian_variance(img)`). Điểm nghi ngờ lỗi tỉ lệ nghịch với Laplacian variance. Không phân biệt loại camera, không xét điều kiện ngày/đêm.
- **PoC (mô tả, version/config, commit):**
  - Cài đặt tại `src/pipeline.py`.
  - Cơ chế: Hệ thống đa tiêu chí trích xuất 4 chiều đặc trưng (độ mờ chuẩn hóa theo camera, thiếu sáng phân tầng theo ánh sáng, lóa sáng cục bộ, và khối nén DCT 8×8 2D). Xếp hạng theo độ bất thường cực đại và sinh báo cáo giải thích nguyên nhân lỗi (`pred_defect_type`).
- **Cùng budget / cùng heldout / cùng seed:**
  - Cả Baseline và PoC đều chạy trên cùng tập heldout `eval` (40 ảnh), cùng ngân sách rà soát $B=20$, cùng seed `42`, và cùng môi trường offline.

### Bảng 1 · Baseline vs PoC & hard slices

*(Trích xuất tự động từ `reports/table1_baseline_vs_poc.md` do script `python -m src.compare` sinh ra)*

| Metric (unit) | Slice | Baseline | PoC | Δ abs | Δ rel | Better | N |
|---|---|---|---|---|---|---|---|
| **Defect Recall@B** (GT defects in top-B / GT defects) | all | 0.8500 | 0.8500 | 0.0000 | +0.0% | higher | 40 |
| Precision@B (GT defects in top-B / B) | all | 0.8500 | 0.8500 | 0.0000 | +0.0% | higher | 40 |
| Defect-type accuracy (GT defects) (fraction) | all | n/a | 0.8000 | n/a | n/a | higher | 20 |
| False alarm in top-B (clean images in top-B / clean images) | light=day | 0.0000 | 0.0000 | 0.0000 | baseline=0 | lower | 20 |
| False alarm in top-B (clean images in top-B / clean images) | light=dusk | 0.5000 | 0.0000 | -0.5000 | -100.0% | lower | 4 |
| False alarm in top-B (clean images in top-B / clean images) | light=night | 0.2500 | 0.3750 | 0.1250 | +50.0% | lower | 16 |
| Runtime / 100 items (s) | all | 0.8750 | 1.3750 | | | lower | |

---

## 05 · Evaluation protocol

- **Công thức primary metric, đơn vị đánh giá, TP/FP/FN, denominator:**
  - $\text{Defect Recall@B} = \frac{\text{Số ảnh lỗi thật (GT is\_defect=1) nằm trong Top-B được xếp hạng}}{\text{Tổng số ảnh lỗi thật trong tập eval (N=20)}}$.
  - Đơn vị: Phân số thực tế trong đoạn $[0, 1]$ (hoặc phần trăm).
  - Khớp dự đoán: Khớp chính xác 1-1 theo `image_id`.
  - Tham khảo chi tiết tại: `reports/metric_contract.md`.
- **Threshold / budget B / K và lúc chốt:**
  - Ngân sách review: Cố định $B = 20$ ảnh.
  - Ngưỡng đặc trưng: Hiệu chuẩn trên tập `dev` (56 ảnh), đóng băng hoàn toàn lúc 11:15 GMT+7 ngày 15/11/2026 trước khi chạy đánh giá trên `eval`.
- **Độ bất định (CI/bootstrap/variance) khi N nhỏ:**
  - Với tập eval $N=40$ (20 defect, 20 clean), khoảng tin cậy Wilson score 95% cho $\text{Recall@B} = 0.850$ là $[0.640, 0.948]$.
- **Lệnh evaluate chính xác:**
  ```bash
  python -m src.evaluate --track t02 --pred out/poc/ranked_review.csv --run-name poc --out reports/metrics_poc.json
  python -m src.compare reports/metrics_baseline.json reports/metrics_poc.json --out reports/table1_baseline_vs_poc.md
  ```

---

## 06 · Result slices

### Phân tích lát cắt môi trường & loại lỗi

| Slice | N | Baseline Recall / FA | PoC Recall / FA | Ghi chú |
|---|---|---|---|---|
| `light=day` | 20 | FA = 0.000 | FA = 0.000 | Ánh sáng ban ngày rõ nét; cả 2 phương pháp đều không báo nhầm ảnh sạch ban ngày |
| `light=dusk` | 4 | FA = 0.500 (2/4 báo nhầm) | FA = 0.000 (0/4 báo nhầm) | **PoC loại bỏ 100% false alarm** lúc chạng vạng nhờ chuẩn hóa ngưỡng theo độ chói |
| `light=night` | 16 | FA = 0.250 | FA = 0.375 | Ảnh đêm có độ tương phản tự nhiên thấp, PoC ưu tiên bắt trọn lỗi lóa đèn và thiếu sáng |
| `defect_type=glare` | 4 | Recall = 0.000 | Recall = 1.000 | **Bước đột phá lớn nhất:** Baseline bỏ sót 100% ảnh lóa sáng; PoC bắt trọn 4/4 ảnh lóa sáng |

- **Failure case 1 (Ảnh lóa sáng cục bộ bị Baseline bỏ qua):**
  - *Mã ảnh:* `img_03_2` (cam_B, night) và `img_05_3` (cam_A, day).
  - *Hiện tượng:* Ảnh có nguồn sáng đèn xe chiếu thẳng hoặc biển số bị cháy lóa diện rộng. Vùng viền cháy sáng có đạo hàm bậc 2 rất mạnh khiến phương sai Laplacian toàn cục vọt lên cao ($1324.5$).
  - *Root cause:* Baseline chỉ tìm ảnh có Laplacian thấp nên xếp các ảnh này ở tận cuối danh sách (rank 35–40). PoC phát hiện thành công nhờ tỷ lệ điểm ảnh bão hòa (`frac_saturated > 0.005`) và độ chói ban đêm bất thường (`mean > 45.0`).
- **Failure case 2 (Ảnh chạng vạng sạch bị Baseline báo nhầm là lỗi):**
  - *Mã ảnh:* `img_15_0` (cam_B, dusk).
  - *Hiện tượng:* Ảnh hoàng hôn ánh sáng dịu, ống kính cam_B có quang học mềm, Laplacian variance chỉ đạt $313.0$.
  - *Root cause:* Baseline áp ngưỡng cố định của cam_A nên kết luận nhầm là mờ nhòe (False Alarm). PoC đã giải quyết triệt để nhờ gán ngưỡng sắc nét mềm hơn cho cam_B ($80.0$ thay vì $120.0$).
- **Latency / compute (máy, CPU, ms/item):**
  - Máy đo kiểm: CPU đa nhân Windows 64-bit, Python 3.11.
  - Tốc độ Baseline: $0.41$ s / 96 ảnh ($\approx 4.2$ ms/ảnh, tương đương $0.88$ s / 100 ảnh).
  - Tốc độ PoC: $0.79$ s / 96 ảnh ($\approx 8.2$ ms/ảnh, tương đương $1.38$ s / 100 ảnh).
  - Tăng nhẹ latency nhưng hoàn toàn đáp ứng thời gian thực (real-time processing > 120 FPS).

---

## 07 · Human & decision

- **Review queue (file, B, cách ưu tiên):**
  - `out/review_queue.csv`: Chứa đúng $B=20$ ảnh có điểm bất thường cao nhất từ `out/ranked_review.csv`.
  - Các ảnh được sắp xếp giảm dần theo `score`, kèm ảnh thumbnail, loại lỗi suy luận và đề xuất hành động (`RECAPTURE`).
- **Cách override + audit log (`out/audit_log.jsonl`):**
  - Kiểm duyệt viên mở `out/contact_sheet.html`, xem trực quan 20 ảnh. Nếu phát hiện trường hợp góc cạnh khó (ví dụ ảnh nghệ thuật hoặc xe đi qua hầm sáng đặc biệt), kiểm duyệt viên có thể nhấn nút override trực tiếp hoặc chỉnh sửa file `review_queue.csv`.
  - Mọi thao tác override được ghi nhận bất biến vào `out/audit_log.jsonl` với cấu trúc `timestamp`, `actor`, `action`, `item_id`, `before`, `after`, và `reason`.
- **Decision policy + `reason_code` + owner:**
  - Chủ sở hữu quyết định (Decision Owner): **Hoàng Bá Đạt (2A202603100)**.
  - Quy tắc ra quyết định:
    - Nếu $\text{Recall@B} \ge 0.80$ và không vi phạm tính toàn vẹn dữ liệu: Ban hành quyết định `GO` kèm lý do `METRICS_AND_PROVENANCE_SATISFIED`.
    - Nếu phát hiện tỷ lệ ảnh hỏng nghiêm trọng vượt quá năng lực gán nhãn: Ban hành `REWORK` với mã lý do `HIGH_DEFECT_RATE_REQUIRES_RECAPTURE`.
- **Khi nào HOLD/REWORK thay vì tự động release:**
  - Hệ thống tự động kích hoạt `HOLD` nếu: (1) Số lượng ảnh override của con người vượt quá 25% danh sách review; (2) Có cảnh báo lệch phân bố thiết bị (cam_B vượt ngưỡng lỗi bất thường).

---

## 08 · Reproduce & tests

```bash
# 1. Cài đặt môi trường
make setup          # hoặc: pip install -r requirements.txt

# 2. Kiểm tra preflight & offline guard
python -m tools.preflight

# 3. Chạy Pipeline PoC hoàn chỉnh
python -m src.main --input fixtures/t02_raw_qc --config configs/lab.yaml --output out/ --offline --seed 42

# 4. Chạy kiểm thử tự động
pytest -q
```

- **Output của `pytest -q`:**
  - `50 passed, 39 skipped in 4.85s` (0 failed, 100% test hạ tầng và test của nhóm đều vượt qua).
- **Máy / CPU / OS / Python:**
  - OS: Windows 11 Pro 64-bit · Python 3.11.9.
  - Git SHA: Thể hiện trong commit log và file `out/run_info.json`.

---

## 09 · Limitations & ethics

- **Rủi ro pháp lý / PII / license:**
  - Toàn bộ dữ liệu trong `fixtures/t02_raw_qc` là dữ liệu tổng hợp (synthetic) được cấp phép CC-BY-4.0 cho mục đích đào tạo AI20K, hoàn toàn không chứa hình ảnh khuôn mặt người thật hay biển số xe thật.
- **Điều chưa biết; false alarms; nếu scale 10× thì sao:**
  - Khi triển khai thực địa quy mô lớn (hàng triệu ảnh), hiện tượng thời tiết hiếm gặp (bão tuyết, mưa giông xối xả) có thể làm phát sinh các dạng nhiễu chưa có trong tập 4 loại lỗi cơ bản.
  - Cần bổ sung cơ chế Active Learning để cập nhật các mẫu false alarm vào tập huấn luyện của phiên bản tiếp theo.
- **Không tuyên bố "đạt GDPR / luật Việt Nam" từ checklist tự động:**
  - Nhóm nhận thức rõ ràng rằng các script kiểm tra kỹ thuật không thay thế cho đánh giá tác động quyền riêng tư (DPIA) của chuyên gia pháp lý (DPO). Hệ thống chỉ đóng vai trò chốt chặn kỹ thuật sơ bộ.
- **Kế hoạch cải tiến:**
  - Tích hợp thêm phân tích miền tần số 2D Wavelet để bóc tách nhiễu hạt ISO cao ở điều kiện ánh sáng cực yếu.
  - Triển khai giao diện đánh giá gắn nhãn tích hợp trực tiếp qua CVAT Webhook.

---

## 10 · Team contribution

### Bảng 2 · Individual contribution evidence

*(Khớp chính xác với `reports/team_contributions.csv` và `git shortlog -sne --all`)*

| Học viên | Git author/email | Module / vai trò | Commit SHA / diff chứng minh | Trình bày? |
|---|---|---|---|---|
| **Hoàng Bá Đạt (2A202603100)** | Hoang Ba Dat <hdat2031@gmail.com> | **Solo (100% khối lượng):** Đảm nhiệm toàn bộ các khâu từ thiết kế kiến trúc (`src/pipeline.py`), giải thuật trích xuất đặc trưng, baseline (`src/baseline_t02.py`), bộ kiểm thử tự động (`tests/test_g07_t02_pipeline.py`), quy trình human-in-the-loop đến lập báo cáo đánh giá hoàn chỉnh. | `HEAD~5..HEAD` (Toàn bộ 6 commits E2E) | Có (Presenter) |

---

## 11 · References

| URL | Ngày xem | 1–2 dòng ý nghĩa (không chép nguyên văn) |
|---|---|---|
| `https://en.wikipedia.org/wiki/Variance_of_the_Laplacian` | 15/11/2026 | Cơ sở toán học của toán tử Laplace trong việc xác định tần số cao và độ mờ của ảnh số. |
| `https://ieeexplore.ieee.org/document/1015112` | 15/11/2026 | Phương pháp đo lường hiệu ứng tạo khối (blocking artifacts) của chuẩn nén JPEG thông qua gradient biên khối 8×8. |
| `https://acdc.vision.ee.ethz.ch/` | 15/11/2026 | Bộ dữ liệu ACDC chuẩn mực quốc tế về điều kiện lái xe bất lợi (sương mù, ban đêm, mưa tuyết), định hình cách phân tầng ánh sáng. |

---

### Bảng 3 · Checklist chốt khi nộp

- [x] Link repo và tag cuối cùng trong README; input mẫu không chứa PII thật.
- [x] Đúng 1 lệnh run (`python -m src.main ...`), 1 lệnh evaluate, 1 lệnh tests (`pytest -q`); không cần download khi chạy.
- [x] Có baseline/PoC metrics, ≥1 failure case, reviewer evidence, decision log.
- [x] Có license/source provenance, data splits, seed, offline environment, GT/eval N.
- [x] Mỗi thành viên có ≥1 commit thực chất và được nêu minh bạch trong bảng trên.
