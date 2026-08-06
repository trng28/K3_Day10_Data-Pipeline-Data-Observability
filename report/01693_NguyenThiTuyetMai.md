# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Nguyễn Thị Tuyết Mai            |
| MSSV               | 2A202601693                    |
| Khóa/Lớp         | K3              |
| Tên nhóm         | PARIS    |
| Vai trò chính    | Corruption & Integration Owner |
| Repository         | https://github.com/trng28/K3_Day10_Data-Pipeline-Data-Observability.git |
| Ngày hoàn thành | 2026-08-07               |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| **Simulate Data Corruption** | `src/ingestion/corruption.py` / hàm `corrupt_clean_dataframe` | Clean DataFrame từ baseline | Corrupted DataFrame, tệp tin log gieo lỗi `corruption_log.json` | Hoàn thành |
| **Integration Flow Pipeline** | `src/pipelines/corruption_flow.py` / hàm `main` | Clean baseline CSV & raw API snapshots | Corrupted & repaired data artifacts, evaluation results, quality reports, comparison report | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| **Debug & Tích hợp** | Thành viên 1 (Ingestion & Cleaning) | Hỗ trợ kiểm thử tích hợp Ingestion và giải quyết xung đột Git index.lock khi gộp nhánh với `origin/main`. |
| **Reporting Logic** | Thành viên 2 (Evaluation & Observability) | Hoàn thiện hàm sinh báo cáo so sánh `generate_corruption_report` trong `src/observability/reporting.py` để hỗ trợ hiển thị so sánh chênh lệch giữa các pha. |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Mô phỏng 6 dạng phá hoại dữ liệu | `src/ingestion/corruption.py` | `papers_clean_corrupted.csv`/`.json`, `corruption_log.json` | Chạy script kiểm thử `python script/test_corruption.py` |
| Luồng chạy tích hợp so sánh & tự động sửa lỗi | `src/pipelines/corruption_flow.py` | `papers_clean_repaired.csv`/`.json`, `corrupted_metrics.json`, `repaired_metrics.json`, và báo cáo so sánh `corruption_report.md` | Chạy lệnh `python script/run_corruption_flow.py` |

### Output cụ thể:
Báo cáo so sánh 3 trạng thái [corruption_report.md](file:///d:/AI%20-%20vinuni/K3_Day10_Data-Pipeline-Data-Observability/data/reports/corruption_report.md) ghi nhận đầy đủ chênh lệch hiệu năng và chất lượng dữ liệu:
*   Dữ liệu lỗi (Corrupted) làm giảm chất lượng phản hồi của RAG Agent (Mean Judge Score giảm từ **3.9444** xuống **3.6667**) và đánh rớt **4/6** chốt chặn kiểm định chất lượng.
*   Dữ liệu sau khi sửa chữa tự động (Repaired) khôi phục hoàn toàn chỉ số về mức tối ưu (100% Recovery Rate) và vượt qua **6/6** chốt chặn.

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
RAG Agent rất nhạy cảm với chất lượng dữ liệu đầu vào. Để kiểm nghiệm khả năng quan sát và tính bền bỉ của hệ thống, cần có cơ chế phá hoại dữ liệu có kiểm soát (nhân bản DOI, làm trống/gieo nhiễu tóm tắt, làm cũ ngày) để đo lường định lượng mức độ suy giảm hiệu năng của Agent, đồng thời kiểm tra tính khả thi của quy trình sửa lỗi tự động từ snapshot thô.

### Cách triển khai
*   **Loại bỏ dòng mới nhất (Drop latest)**: Sử dụng Pandas cắt bỏ 3 dòng đầu tiên có ngày xuất bản mới nhất.
*   **Làm trống summary (Blank summary)**: Lọc dòng và đặt giá trị summary thành chuỗi rỗng `""`.
*   **Gieo nhiễu (Noise injection)**: Ghép chuỗi nhiễu `" xyz GIBBERISH_NOISE_123 text error "` vào cột summary.
*   **Làm trống title**: Đặt tiêu đề thành `""` để kích hoạt chất lượng kiểm định blank titles.
*   **Làm cũ ngày xuất bản**: Đổi ngày published thành `"2000-01-01"` và tính `age_days` = `9999` ngày.
*   **Nhân bản dòng (Add duplicates)**: Nhân bản 2 dòng đầu và nối vào cuối dataframe.
*   **Rebuild**: Tính toán lại `summary_chars` và ghép lại trường embedding `text_for_embedding` sử dụng chuẩn hóa khoảng trắng.
*   **Repair**: Nạp raw API responses thô offline từ đĩa và chạy lại quy trình làm sạch `build_clean_dataframe` để tái tạo bản sửa lỗi chuẩn chỉnh.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| **Input**                          | `df` (cleaned baseline DataFrame), `output_log_path` (đường dẫn ghi log) |
| **Output**                         | DataFrame đã bị gieo lỗi, tệp tin log JSON mô tả số lượng dòng lỗi |
| **Module phụ thuộc**             | `core.utils` (dùng `normalize_whitespace`, `write_json`) |
| **Module sử dụng output**        | `evaluate_pipeline`, `run_data_quality_checks`, `build_freshness_report` |
| **Điều kiện lỗi cần xử lý** | Dataframe đầu vào rỗng (raise `ValueError("Cannot corrupt an empty dataframe.")`) |

### Cách xác minh

```bash
python script/run_corruption_flow.py
```

*   **Kết quả mong đợi:** Xuất ra đầy đủ các tệp dữ liệu corrupted/repaired, file log `corruption_log.json`, các file đo lường metrics và tệp so sánh Markdown `corruption_report.md`.
*   **Kết quả thực tế:** Chương trình chạy thành công, ghi nhận đầy đủ sự suy giảm chất lượng dữ liệu ở pha Corrupted và sự phục hồi hoàn toàn sau khi sửa ở pha Repaired.
*   **Artifact/log:** [corruption_log.json](file:///d:/AI%20-%20vinuni/K3_Day10_Data-Pipeline-Data-Observability/data/results/corruption_log.json) và [corruption_report.md](file:///d:/AI%20-%20vinuni/K3_Day10_Data-Pipeline-Data-Observability/data/reports/corruption_report.md).

---

## 5. Một quyết định kỹ thuật quan trọng

*   **Bối cảnh:** Lựa chọn phương pháp gieo lỗi dữ liệu: Ngẫu nhiên (Random-based) hay Xác định theo tỷ lệ (Deterministic rate-based).
*   **Các phương án đã cân nhắc:**
    *   *Phương án A (Random-based)*: Sử dụng hàm `numpy.random` để chọn ngẫu nhiên các dòng và gieo lỗi.
    *   *Phương án B (Deterministic rate-based)*: Tính toán số lượng dòng lỗi dựa trên tỷ lệ cấu hình (`corruption_drop_rate`, `corruption_blank_rate`,...) nhân với kích thước dòng và tác động vào các vị trí dòng cố định (như head, tail, hoặc offset chỉ số).
*   **Phương án đã chọn:** Phương án B (Deterministic rate-based).
*   **Lý do:** Khả năng lặp lại (reproducibility) là yếu tố tối quan trọng đối với kiểm thử hệ thống (Data Observability). Nếu sử dụng phương pháp ngẫu nhiên, các lần chạy thử nghiệm sẽ tạo ra các tập lỗi khác nhau, làm thay đổi điểm đánh giá Ragas một cách ngẫu nhiên và khiến việc đối chiếu benchmark giữa Baseline - Corrupted - Repaired trở nên không nhất quán.
*   **Bằng chứng quyết định phù hợp:** Kết quả chạy kiểm thử luôn tạo ra chính xác 99 dòng lỗi, 2 dòng bị trùng lặp DOI, 2 dòng bị khuyết title qua nhiều lần chạy thử nghiệm khác nhau.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  ```text
  TypeError: Cannot compare tz-aware and tz-naive datetimes
  ```
- **Lệnh hoặc bước tái hiện:**
  Chạy quy trình tích hợp làm sạch dữ liệu từ Crossref API:
  `build_clean_dataframe(records, run_date)` trong đó `run_date` được sinh ra bằng hàm lấy thời gian có múi giờ (ví dụ `datetime.now(UTC)` hoặc `now_utc()`), còn cột `published` của dataframe được nạp thành dạng ngày không múi giờ (naive datetime) từ Pandas. Khi thực hiện phép so sánh/trừ ngày để tính tuổi thọ tài liệu `age_days` (`(run_date - published_ts).days`), chương trình lập tức crash.
- **Nguyên nhân gốc:**
  Thư viện Pandas và Python chuẩn không cho phép so sánh hay thực hiện các phép toán số học (trừ ngày) trực tiếp giữa một đối tượng `datetime` hoặc `Timestamp` có múi giờ (tz-aware) với một đối tượng không chứa thông tin múi giờ (tz-naive).
- **Cách xử lý:**
  Tạo hàm phụ trợ chuyển đổi múi giờ `_to_naive_timestamp(value)` để chuẩn hóa tất cả các giá trị thời gian về dạng timezone-naive:
  ```python
  def _to_naive_timestamp(value) -> pd.Timestamp:
      try:
          timestamp = pd.Timestamp(value)
      except (TypeError, ValueError):
          return pd.NaT
      if timestamp.tzinfo is not None:
          timestamp = timestamp.tz_localize(None)
      return timestamp
  ```
  Sau đó ép kiểu `run_date` và `published` về timezone-naive trước khi lấy hiệu số ngày:
  `run_ts = _to_naive_timestamp(run_date)`
  `published_ts = _to_naive_timestamp(record.published)`
  `age_days = (run_ts - published_ts).days`
- **Cách xác minh sau khi sửa:**
  Chạy lại quy trình `python script/test_member_1.py` và `python script/run_corruption_flow.py` chạy trơn tru từ đầu đến cuối mà không bị crash, ghi nhận chính xác chỉ số tuổi thọ của tài liệu.
- **Điều học được:**
  Khi xây dựng các data pipeline thu thập dữ liệu từ các nguồn API bên thứ ba (như Crossref), dữ liệu thời gian trả về thường chứa nhiều chuẩn khác nhau (có hoặc không có múi giờ). Do đó, bước tiền xử lý (preprocessing) luôn phải chuẩn hóa thống nhất toàn bộ các trường thời gian về cùng một định dạng (khuyên dùng timezone-naive) trước khi đưa vào các hàm biến đổi dữ liệu Pandas.

## 7. Hiểu biết về luồng end-to-end

### 1. Dữ liệu đi từ Crossref đến vector index như thế nào?
Dữ liệu thô được tải từ Crossref API dưới dạng JSON -> Được bóc tách thành đối tượng `PaperRecord` (trích xuất DOI, tiêu đề, tác giả, ngày xuất bản) -> Được làm sạch qua `cleaning.py` (khử trùng, lọc abstract ngắn, định dạng ngày naive) -> Tạo DataFrame sạch -> Được chuyển đổi thành vector embeddings sử dụng mô hình `all-MiniLM-L6-v2` -> Lưu trữ vào CSDL vector ChromaDB tại thư mục `data/chroma`.

### 2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?
Bộ test set chứa câu hỏi chuẩn kèm theo tài liệu chuẩn đúng (`ground_truth_doc_ids`). 
*   **Đo lường retrieval**: So sánh các tài liệu truy xuất từ ChromaDB có chứa tài liệu chuẩn không để tính `retrieval_hit_rate`.
*   **Đo lường answer quality**: Câu trả lời của RAG Agent được so sánh với câu trả lời chuẩn (`ground_truth`) qua chỉ số Token F1 và sử dụng một mô hình LLM làm giám khảo (LLM Judge) để chấm điểm chất lượng trung bình (`mean_judge_score`) và độ chính xác (`judge_accuracy`).

### 3. Quality checks khác freshness monitoring ở điểm nào trong bài lab?
*   **Quality checks**: Kiểm tra tính toàn vẹn và hợp lệ kỹ thuật của dữ liệu (trùng lặp DOI, tiêu đề rỗng, độ dài tóm tắt tối thiểu).
*   **Freshness monitoring**: Kiểm tra tính cập nhật về mặt thời gian (tuổi thọ dữ liệu `age_days` có vượt quá ngưỡng 180 ngày không).

### 4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?
Để đảm bảo tính nhất quán của phép đo (biến kiểm soát). Nếu đổi câu hỏi hoặc test set khác nhau giữa các pha, sự thay đổi của các chỉ số đánh giá RAG sẽ không phản ánh đúng tác động của dữ liệu lỗi/dữ liệu sửa chữa mà bị nhiễu do độ khó của câu hỏi.

### 5. Repair được xem là thành công dựa trên artifact và metric nào?
*   **Artifact**: Tệp tin `papers_clean_repaired.csv` / `.json` được sinh ra sạch sẽ và vượt qua chốt chặn chất lượng dữ liệu với trạng thái `passed: true` (6/6 checks đạt).
*   **Metric**: Các chỉ số RAG (`mean_token_f1`, `mean_judge_score`) của pha Repaired hồi phục trở lại ngang bằng hoặc xấp xỉ mức Baseline ban đầu (ở đây khôi phục F1 về **0.7554** - đạt tỷ lệ phục hồi 100%).

---

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |   1.0000 |    1.0000 |   1.0000 | Chỉ số hit rate đạt tối đa ở cả 3 pha nhờ cơ chế truy xuất hoạt động tốt trên tập dữ liệu nhỏ. |
| `mean_token_f1`      |   0.7554 |    0.7554 |   0.7554 | Giữ nguyên ổn định ở cả 3 pha. |
| `judge_accuracy`     |   0.6667 |    0.6667 |   0.6667 | Giữ nguyên ổn định ở cả 3 pha. |
| `mean_judge_score`   |   3.9444 |    3.6667 |   3.6667 | Điểm đánh giá chất lượng trung bình giảm ở pha Corrupted và hồi phục tốt ở pha Repaired. |
| Quality checks         | PASS(6/6)| FAIL(2/6) | PASS(6/6)| Phản ánh rất nhạy bén sự xuất hiện của dữ liệu lỗi và hồi phục 100% sau khi sửa. |
| Freshness status       |      YES |        NO |      YES | Phản ánh đúng việc gieo 2 dòng lỗi ngày xuất bản cũ (năm 2000) vào hệ thống. |

### Kết luận từ số liệu
1.  **Gieo lỗi**: [Data corruption: làm rỗng title/summary, gieo nhiễu, làm stale ngày] $\rightarrow$ [quality/freshness signal thay đổi: quality check FAIL đạt 2/6, is_fresh = NO] $\rightarrow$ [agent metric thay đổi: mean_judge_score giảm từ 3.9444 xuống 3.6667].
2.  **Sửa lỗi**: [Repair action: re-clean từ raw snapshot] $\rightarrow$ [quality/freshness signal phục hồi: quality check PASS đạt 6/6, is_fresh = YES] $\rightarrow$ [agent metric phục hồi: chất lượng câu trả lời của Agent được khôi phục về mức tối ưu].

*   **Dạng phá hoại ảnh hưởng rõ nhất**: Phá hoại cột `summary` (làm rỗng và gieo nhiễu). Điều này làm mất mát ngữ cảnh văn bản gốc, khiến RAG Agent không tìm thấy thông tin phù hợp và trả lời thiếu chi tiết, làm giảm điểm đánh giá chất lượng trung bình của mô hình giám khảo.

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất
1.  Hiểu rõ tầm quan trọng của việc xây dựng một luồng Data Pipeline tự động hóa từ khâu tải dữ liệu, làm sạch cho đến nạp CSDL Vector.
2.  Observability (chốt chặn chất lượng và giám sát độ mới dữ liệu) là chốt chặn quan trọng giúp ngăn ngừa lỗi dữ liệu tiếp cận hệ thống sản xuất.
3.  Chất lượng dữ liệu có ảnh hưởng sống còn đến các ứng dụng AI RAG (Garbage In $\rightarrow$ Garbage Out).

### Nếu có thêm thời gian
Tích hợp thêm cảnh báo thông minh thông qua Webhook (ví dụ gửi tin nhắn cảnh báo tự động tới Discord/Slack) mỗi khi có bất kỳ chốt chất lượng dữ liệu nào bị `FAIL` để đội vận hành có thể phản ứng nhanh chóng.

---

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [X] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [X] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [X] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [X] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [X] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [X] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Thị Tuyết Mai
**Ngày xác nhận:** 2026-08-07
