# Báo cáo cá nhân - Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Nguyễn Thị Khánh Ly |
| MSSV | 2A202601403 |
| Khóa/Lớp | K3 |
| Vai trò chính | Evaluation & Observability Owner |
| Repository | https://github.com/trng28/K3_Day10_Data-Pipeline-Data-Observability |
| Branch/PR | `evaluation-observability` |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

Tôi phụ trách phần đánh giá và quan sát chất lượng dữ liệu cho pipeline RAG. Phần việc tập trung vào việc tạo evaluation set, kiểm tra chất lượng dữ liệu, theo dõi freshness và sinh báo cáo Markdown để nhóm có thể đọc kết quả một cách rõ ràng.

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Evaluation set | `src/evaluation/testset.py` - `build_test_set()` | Cleaned dataframe từ bước cleaning | `data/eval/test_set.json` với câu hỏi, ground truth và document IDs | Hoàn thành |
| Data quality | `src/observability/quality.py` - `run_data_quality_checks()` | Cleaned dataframe và `Settings` | Quality report JSON trong `data/quality/` | Hoàn thành |
| Freshness report | `src/observability/quality.py` - `build_freshness_report()` | Cột `published`, threshold freshness | Freshness report JSON | Hoàn thành |
| Baseline report | `src/observability/reporting.py` - `generate_phase1_report()` | Source summary, metrics, quality, freshness | `data/reports/phase1_report.md` | Hoàn thành |
| Corruption report | `src/observability/reporting.py` - `generate_corruption_report()` | Metrics và quality/freshness của baseline, corrupted, repaired | `data/reports/corruption_report.md` | Hoàn thành phần hàm |

## 3. Kết quả đã bàn giao

| Nhiệm vụ | File/hàm/artifact liên quan | Kết quả | Cách xác minh |
| --- | --- | --- | --- |
| Tạo evaluation set từ dữ liệu sạch | `build_test_set()` | Sinh câu hỏi thuộc các nhóm `summary`, `authors`, `date`, `categories` | `uv run --extra dev pytest tests/test_member2.py -q` |
| Kiểm tra chất lượng dữ liệu | `run_data_quality_checks()` | Phát hiện row rỗng, ID thiếu/trùng, title thiếu, summary quá ngắn, dữ liệu quá cũ | `data/quality/baseline_quality.json` |
| Theo dõi freshness | `build_freshness_report()` | Ghi latest/oldest published date, stale rows, invalid date rows, trạng thái `is_fresh` | `data/quality/freshness_report.json` |
| Sinh báo cáo baseline | `generate_phase1_report()` | Tổng hợp source, metrics, quality và freshness thành Markdown | `data/reports/phase1_report.md` |
| Sinh báo cáo so sánh corruption | `generate_corruption_report()` | Chuẩn bị bảng so sánh baseline/corrupted/repaired và delta metrics | Kiểm thử trong `tests/test_member2.py` |

Output cụ thể đã xác minh trong baseline:

- Clean records: `24`
- Evaluation samples: `18`
- Retrieval hit rate: `1.0000`
- Mean token F1: `0.7554`
- Judge accuracy: `0.6667`
- Mean judge score: `3.9444`
- Quality checks: `PASS (6/6)`
- Freshness: `PASS`, stale rows `0/24`

## 4. Giải thích kỹ thuật

### Vấn đề cần giải quyết

Pipeline RAG không chỉ cần chạy được mà còn cần đo được chất lượng. Nếu dữ liệu bị thiếu, trùng ID, summary rỗng hoặc quá cũ, agent có thể trả lời sai nhưng người dùng khó nhận ra nguyên nhân. Vì vậy phần của tôi tạo ra các artifact đánh giá và quan sát để nhóm có thể chứng minh chất lượng pipeline bằng số liệu.

### Cách triển khai

Trong `build_test_set()`, tôi kiểm tra schema đầu vào trước khi tạo câu hỏi. Các dòng không hợp lệ như thiếu `paper_id`, `title`, `summary` hoặc trùng `paper_id` được loại bỏ khỏi tập ứng viên. Hàm chọn tối đa 6 paper theo cách deterministic để khi chạy lại với cùng dữ liệu thì test set ổn định. Mỗi paper tạo nhiều loại câu hỏi để đánh giá nhiều mặt của agent: tóm tắt nội dung, tác giả, ngày công bố và category.

Trong `run_data_quality_checks()`, tôi triển khai các check cơ bản nhưng quan trọng: số dòng, ID không rỗng, ID không trùng, title không rỗng, summary đủ dài, và `age_days` không vượt ngưỡng freshness. Nếu dataframe thiếu cột, hàm ghi nhận check fail rõ ràng thay vì làm pipeline crash.

Trong `build_freshness_report()`, tôi parse `published` về datetime UTC, tính stale rows theo `settings.freshness_threshold_days`, đếm invalid dates và ghi trạng thái `is_fresh`.

Trong `reporting.py`, tôi sinh báo cáo Markdown cho baseline và corruption flow. Báo cáo baseline tập trung vào source, metrics, data quality và freshness. Báo cáo corruption flow so sánh baseline, corrupted và repaired, kèm delta so với baseline để thấy data corruption ảnh hưởng đến RAG như thế nào.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | Cleaned dataframe có các cột `paper_id`, `title`, `summary`, `authors_joined`, `categories_joined`, `published`, `age_days` |
| Output | Evaluation JSON, quality JSON, freshness JSON, Markdown reports |
| Module phụ thuộc | `src/ingestion/cleaning.py`, `src/core/config.py`, `src/core/utils.py` |
| Module sử dụng output | `src/evaluation/metrics.py`, `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py` |
| Điều kiện lỗi cần xử lý | Thiếu cột, dữ liệu rỗng, duplicate `paper_id`, summary quá ngắn, `age_days` invalid hoặc quá cũ |

## 5. Xác minh

Các lệnh đã chạy:

```powershell
uv run --extra dev pytest tests/test_member2.py -q
uv run pytest -q
uv run python -m compileall -q src tests
```

Kết quả:

```text
4 passed
```

Ngoài ra, sau khi branch `main` thay đổi, tôi đã rebase branch `evaluation-observability`, xử lý conflict trong 3 file được phân công và push lại. Pull request hiện chỉ chứa đúng 3 file source:

```text
src/evaluation/testset.py
src/observability/quality.py
src/observability/reporting.py
```

## 6. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Evaluation set cần ổn định để so sánh baseline, corrupted và repaired. Nếu mỗi lần chạy sinh câu hỏi khác nhau thì metrics sẽ khó so sánh.
- **Các phương án cân nhắc:** Chọn random paper hoặc chọn deterministic từ cleaned dataframe.
- **Phương án đã chọn:** Chọn deterministic bằng các vị trí phân bố đều trong dataset.
- **Lý do:** Cách này giúp test set có thể tái lập, vẫn bao phủ nhiều vị trí trong corpus và không cần seed random.
- **Bằng chứng:** Test `test_build_test_set_is_deterministic_and_complete` xác minh số lượng câu hỏi, loại câu hỏi và document IDs ổn định.

## 7. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** Khi tạo pull request, GitHub báo `Can't automatically merge`.
- **Nguyên nhân gốc:** Branch `main` đã có commit mới sửa cùng các file `testset.py`, `quality.py`, `reporting.py`, gây conflict khi so sánh PR.
- **Cách xử lý:** Fetch `origin/main`, rebase branch `evaluation-observability`, gỡ conflict thủ công trong 3 file được phân công, giữ phần triển khai đầy đủ hơn và tương thích với contract hiện có.
- **Cách xác minh sau khi sửa:** Chạy lại test và compile, sau đó force-push bằng `git push --force-with-lease origin evaluation-observability`.
- **Kết quả:** Branch đã cập nhật trên GitHub và PR chỉ còn đúng 3 file source.

## 8. Hiểu biết về luồng end-to-end

Dữ liệu bắt đầu từ Crossref API, sau đó được lưu thành raw response và raw records để có thể truy vết. Bước cleaning chuẩn hóa dữ liệu thành cleaned dataframe, tạo các trường như `paper_id`, `summary`, `published`, `age_days` và text dùng cho embedding. Sau đó retrieval module build embedding và nạp vào vector index để agent tìm tài liệu liên quan khi trả lời câu hỏi.

Evaluation set là bộ câu hỏi có ground truth và `ground_truth_doc_ids`. Khi agent trả lời, evaluator kiểm tra tài liệu retrieve được có chứa document ID đúng không, đồng thời tính token F1 và judge score để đánh giá chất lượng câu trả lời.

Quality checks tập trung vào độ hợp lệ của dữ liệu như thiếu ID, trùng ID, summary ngắn hoặc dữ liệu quá cũ. Freshness monitoring tập trung riêng vào độ mới của dữ liệu theo ngày published và ngưỡng freshness. Hai phần này bổ sung cho nhau: quality cho biết dữ liệu có sạch không, freshness cho biết dữ liệu có còn đủ mới không.

Cần dùng cùng test set cho baseline, corrupted và repaired vì chỉ khi câu hỏi giống nhau thì metrics mới so sánh công bằng. Nếu corruption làm metric giảm và repair làm metric phục hồi, nhóm có bằng chứng rõ ràng rằng chất lượng dữ liệu ảnh hưởng trực tiếp đến chất lượng agent.

## 9. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | `1.0000` | Chưa có artifact | Chưa có artifact | Baseline retrieve đúng document cho toàn bộ sample đã đánh giá. |
| `mean_token_f1` | `0.7554` | Chưa có artifact | Chưa có artifact | Câu trả lời có mức overlap tốt với ground truth nhưng vẫn còn dư địa cải thiện. |
| `judge_accuracy` | `0.6667` | Chưa có artifact | Chưa có artifact | Judge đánh giá khoảng 2/3 câu trả lời là đúng về mặt nội dung. |
| `mean_judge_score` | `3.9444` | Chưa có artifact | Chưa có artifact | Điểm trung bình khá tốt cho baseline. |
| Quality checks | `PASS 6/6` | Chưa có artifact | Chưa có artifact | Dữ liệu baseline không có lỗi cơ bản về completeness, uniqueness và freshness. |
| Freshness status | `PASS` | Chưa có artifact | Chưa có artifact | Không có stale rows trong baseline. |

### Kết luận từ số liệu

Baseline hiện có chất lượng dữ liệu tốt: 24 clean records, quality checks pass 6/6 và stale rows bằng 0. Retrieval hit rate đạt 1.0, nghĩa là với test set hiện tại, retriever tìm được đúng document ground truth cho tất cả câu hỏi.

Phần corrupted và repaired chưa có artifact cuối cùng trong repository tại thời điểm viết báo cáo cá nhân, nên tôi không ghi kết luận định lượng cho hai trạng thái này. Khi nhóm hoàn thành corruption flow, cần chạy lại cùng test set để điền các cột corrupted/repaired và so sánh delta với baseline.

## 10. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Evaluation set cần có document IDs ổn định, nếu không retrieval metric sẽ không đáng tin.
2. Data quality report nên fail rõ ràng khi thiếu cột hoặc dữ liệu lỗi, vì crash không cung cấp đủ bằng chứng để debug pipeline.
3. Với RAG agent, chất lượng dữ liệu đầu vào ảnh hưởng trực tiếp đến khả năng retrieve đúng tài liệu và trả lời đúng nội dung.

### Nếu có thêm thời gian

Tôi muốn mở rộng quality checks bằng Great Expectations hoặc rule chi tiết hơn cho abstract/summary, ví dụ kiểm tra text quá nhiễu, category rỗng theo tỷ lệ, hoặc `published` nằm ngoài khoảng hợp lý. Sau đó có thể theo dõi sự thay đổi các check này giữa baseline, corrupted và repaired.

## 11. Cam kết cá nhân

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Các kết luận về baseline có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi đã chạy thành công cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Thị Khánh Ly  
**Ngày xác nhận:** 2026-08-06
