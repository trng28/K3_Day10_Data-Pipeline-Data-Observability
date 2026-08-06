# Member Role Report — Day 10: Data Pipeline & Data Observability

> Mỗi thành viên trong nhóm tự hoàn thành mẫu này để báo cáo đúng vai trò, phần việc và mức hiểu của mình. Không sao chép nguyên báo cáo chung hoặc báo cáo của thành viên khác. Thay nội dung trong dấu `[ ]` và xóa các dòng hướng dẫn không cần thiết trước khi nộp.

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Nguyễn Mai Thanh Trúc            |
| MSSV               | 2A202601473                   |
| Khóa/Lớp         | K3              |
| Tên nhóm         | PARIS    |
| Vai trò chính    | Pipeline Integration & Observability Demo (orchestration corruption→repair, resilient embeddings, demo dashboard) |
| Repository         | https://github.com/trng28/K3_Day10_Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-08-06               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Corruption → repair orchestration | `src/pipelines/corruption_flow.py` | `papers_clean.csv` + `baseline_metrics.json` + `crossref_records.json` | `papers_clean_corrupted/repaired.{csv,json}`, `corrupted/repaired_metrics.json`, `data/reports/corruption_report.md` | Hoàn thành |
| Resilient OpenAI embeddings adapter | `src/retrieval/embeddings.py` (`ConfiguredEmbeddings`) | `text_for_embedding` batch từ cleaning stage | Vector 1536d cho ChromaDB (OpenAI hoặc local hash fallback cùng chiều) | Hoàn thành |
| Demo dashboard & pipeline runner | `demo/server.py`, `frontend/src/App.tsx` | Artifacts trong `data/results`, `data/quality`, `data/raw`, `data/clean` | API `/api/dashboard`, `/api/run/*`, `/api/chat`; UI xem metrics/quality/freshness và chạy lại pipeline | Hoàn thành |
| Fix corruption test | `script/test_corruption.py` | Output thực tế của `corrupt_clean_dataframe` | Test pass đúng với marker/threshold thực tế | Hoàn thành |

Chỉ nhận ownership cho phần bạn trực tiếp thực hiện. Liên hệ rõ phần việc của bạn với đầu vào, đầu ra và các thành viên phụ thuộc vào phần đó.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Merge PR #2 (evaluation/observability) và PR #3 (corruption integration), giải quyết merge conflict giữa `feat/corruption-integration` và `main` | Module ingestion/corruption (bạn `unknown@nguyenmai2005hx`) và evaluation/observability (bạn `ngnkhanhly7`) | Cả hai nhánh hợp nhất chạy được end-to-end, không mất artifact của nhau (commit `791c41c`, `1351473`) |
| Viết tài liệu kiến trúc tổng thể pipeline | Toàn nhóm | `data-pipeline-observability-architecture.md` mô tả luồng và cấu hình khớp source code hiện tại |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Nối flow corrupt → re-index → evaluate → quality/freshness → repair → re-index → evaluate → quality/freshness → report | `src/pipelines/corruption_flow.py` | `data/reports/corruption_report.md`, `data/results/{corrupted,repaired}_metrics.json` | `uv run python script/run_corruption_flow.py` |
| Thêm fallback embedding cục bộ khi OpenAI API mất kết nối/timeout, giữ nguyên chiều vector | `src/retrieval/embeddings.py` | Index vẫn build được kể cả khi `APIConnectionError`/`APITimeoutError` | Ngắt mạng tạm thời rồi chạy `run_phase1.py`, quan sát log `WARNING: OpenAI embeddings are unreachable...` |
| Dựng dashboard demo chạy pipeline và chat với agent qua UI | `demo/server.py`, `frontend/src/App.tsx` | Dashboard hiển thị baseline/corrupted/repaired song song | `python demo/server.py` rồi mở `http://127.0.0.1:8787` |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

`data/reports/corruption_report.md` — báo cáo so sánh baseline/corrupted/repaired do `corruption_flow.py` sinh ra, tổng hợp cả metric đánh giá và trạng thái quality/freshness cho 3 trạng thái dữ liệu trong một lần chạy.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Hai vấn đề chính: (1) baseline, corruption và repair là ba script/module tách rời do các thành viên khác nhau viết — cần một orchestration duy nhất chạy đúng thứ tự và dùng lại đúng test set để so sánh công bằng; (2) `EMBEDDING_PROVIDER=openai` phụ thuộc mạng ra ngoài, trong khi máy lab có thể mất kết nối/timeout giữa lúc build index, làm crash toàn bộ pipeline.

### Cách triển khai

- `corruption_flow.py`: đọc `clean_csv` và `baseline_metrics` đã có sẵn (raise lỗi rõ ràng nếu chưa chạy baseline), gọi `corrupt_clean_dataframe` với các rate cấu hình qua `.env` (`CORRUPTION_DROP_RATE`, `BLANK_RATE`, `NOISE_RATE`, `STALE_RATE`, `DUPLICATE_RATE`), ghi lại corruption log, build lại `LocalEmbeddingIndex` cho tập corrupted, chạy `evaluate_pipeline` với **cùng** `eval_testset` dùng cho baseline, rồi chạy `run_data_quality_checks`/`build_freshness_report`. Bước repair không "vá" dữ liệu corrupted mà build lại từ `raw_records_json` gốc (nguồn tin cậy), lặp lại đúng quy trình evaluate/quality/freshness, sau đó `generate_corruption_report` tổng hợp cả 3 trạng thái vào một Markdown.
- `ConfiguredEmbeddings` (`embeddings.py`): tách provider embedding khỏi provider LLM. Khi `EMBEDDING_PROVIDER=openai`, chỉ bắt hai lỗi mạng cụ thể (`APIConnectionError`, `APITimeoutError`, `max_retries=0` để fail nhanh) rồi chuyển sang `_hash_embedding` — một hàm hashing token/bigram bằng blake2b, cố định ở đúng 1536 chiều (bằng `text-embedding-3-small`) để collection ChromaDB không bị lệch dimension giữa các lần chạy.
- `demo/server.py`: expose `/api/run/{crawl,baseline,comparison,all}` chạy từng script bằng `subprocess.Popen` và stream log qua NDJSON, `/api/dashboard` gộp metrics + quality + freshness của 3 trạng thái để frontend vẽ so sánh, `/api/chat` gọi lại `answer_question` trên index baseline đã build.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | `data/clean/papers_clean.csv`, `data/results/baseline_metrics.json`, `data/raw/crossref_records.json`, `data/eval/test_set.json` |
| Output                         | `data/clean/papers_clean_{corrupted,repaired}.{csv,json}`, `data/embeddings/papers_embeddings_{corrupted,repaired}.json`, `data/results/{corrupted,repaired}_{metrics,answers}.json`, `data/quality/{corrupted,repaired}.json`, `data/quality/{corrupted,repaired}_freshness.json`, `data/reports/corruption_report.md` |
| Module phụ thuộc             | `ingestion.corruption`, `ingestion.cleaning`, `retrieval.index.LocalEmbeddingIndex`, `evaluation.metrics.evaluate_pipeline`, `observability.quality`, `observability.reporting` |
| Module sử dụng output        | `demo/server.py` (dashboard), `frontend/src/App.tsx`, `report/group_report.md` |
| Điều kiện lỗi cần xử lý | Chưa chạy baseline trước (raise `RuntimeError`); OpenAI embeddings mất kết nối/timeout giữa batch (fallback hash, log warning, không crash); step con trong demo server trả exit code != 0 (dừng chuỗi step, trả log cho UI) |

### Cách xác minh

```bash
uv run python script/run_phase1.py
uv run python script/run_corruption_flow.py
uv run python script/test_corruption.py
python demo/server.py   # mở http://127.0.0.1:8787
```

- **Kết quả mong đợi:** `run_corruption_flow.py` in ra số dòng corrupted/repaired, metrics tương ứng và đường dẫn `corruption_report.md`; dashboard hiển thị đủ 3 trạng thái baseline/corrupted/repaired.
- **Kết quả thực tế:** Chạy thành công, sinh `data/reports/corruption_report.md` với bảng so sánh; `data/results/repaired_metrics.json` cho thấy metric phục hồi so với `corrupted_metrics.json`.
- **Artifact/log:** `data/reports/corruption_report.md`, `data/results/corrupted_metrics.json`, `data/results/repaired_metrics.json` (không chứa secret).

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** `EMBEDDING_PROVIDER=openai` cần gọi API ra ngoài để build/re-build 3 collection (baseline/corrupted/repaired) trong một lần chạy `corruption_flow.py`; máy lab có thể mất mạng hoặc bị timeout giữa các batch.
- **Các phương án đã cân nhắc:** (1) Tăng `max_retries`/timeout của `OpenAIEmbeddings` và để pipeline dừng nếu vẫn lỗi; (2) Bắt lỗi mạng và fallback sang embedding cục bộ (hash-based) giữ đúng 1536 chiều của `text-embedding-3-small`.
- **Phương án đã chọn:** (2) — fallback cục bộ, chỉ bắt `APIConnectionError`/`APITimeoutError` (không bắt lỗi auth/quota để tránh che lỗi cấu hình sai key).
- **Lý do:** Ưu tiên pipeline chạy hết được end-to-end để có đủ artifact so sánh baseline/corrupted/repaired trong buổi lab, thay vì dừng giữa chừng vì lỗi mạng tạm thời; giữ đúng dimension để không phải rebuild lại các collection đã tạo trước đó.
- **Bằng chứng quyết định phù hợp:** `run_corruption_flow.py` vẫn sinh đủ `corrupted_metrics.json` và `repaired_metrics.json` khi test thủ công bằng cách ngắt mạng giữa lúc build index; log in ra đúng cảnh báo `WARNING: OpenAI embeddings are unreachable...` thay vì traceback crash.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `script/test_corruption.py` fail ở các `assert` kiểm tra corruption (ví dụ tìm marker string và ngày stale không khớp với dữ liệu thực tế do `corrupt_clean_dataframe` sinh ra).
- **Lệnh hoặc bước tái hiện:** `uv run python script/test_corruption.py` sau khi `ingestion/corruption.py` được merge từ nhánh khác.
- **Nguyên nhân gốc:** Test được viết trước, dựa trên giả định về marker/format lỗi (chuỗi đánh dấu noise, độ dài title bị cắt, ngày stale cụ thể) khác với implementation thật của `corrupt_clean_dataframe` sau khi teammate hoàn thiện logic corruption — không phải do logic corruption sai, mà do assertion trong test không đồng bộ với output thật.
- **Cách xử lý:** Sửa lại các assertion trong `test_corruption.py` để khớp đúng output thực tế: marker noise `CORRUPTED_TOKEN` trong `summary`, title bị cắt còn `<= 28` ký tự, ngày `published` bị đổi thành `2016-01-01`, và đếm duplicate qua `paper_id.nunique()` thay vì so sánh trực tiếp không đúng công thức.
- **Cách xác minh sau khi sửa:** Chạy lại `uv run python script/test_corruption.py`, tất cả assertion pass và in ra "KIỂM THỬ CORRUPTION THÀNH CÔNG" (commit `3499bad`).
- **Điều học được:** Test cho một hàm sinh dữ liệu lỗi (corruption) phải được viết/kiểm lại đối chiếu trực tiếp với implementation cuối cùng, không suy đoán format lỗi từ tên biến hoặc docstring, vì các giá trị cụ thể (marker, ngày, ngưỡng) là chi tiết cài đặt dễ thay đổi giữa các lần refactor.

## 7. Hiểu biết về luồng end-to-end

Giải thích ngắn gọn bằng lời của bạn:

1. Dữ liệu đi từ Crossref đến vector index như thế nào?
2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?
3. Quality checks khác freshness monitoring ở điểm nào trong bài lab?
4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?
5. Repair được xem là thành công dựa trên artifact và metric nào?

**Câu trả lời:**

1. Crossref API (`GET /works` với query + filter ngày/abstract) → `raw/crossref_response.json` + `raw/crossref_records.json` → `ingestion/cleaning.py` validate/normalize (DOI, title, abstract, `published`), dedupe theo `paper_id`, tạo `text_for_embedding` → `data/clean/papers_clean.{csv,json}` → `ConfiguredEmbeddings` sinh vector (OpenAI `text-embedding-3-small`, hoặc fallback hash 1536d) → `LocalEmbeddingIndex` ghi vào ChromaDB (collection `papers-baseline`, HNSW, cosine) và lưu manifest `papers_embeddings.json`.
2. `evaluation/testset.py` sinh `data/eval/test_set.json` với các câu hỏi gắn sẵn `ground_truth_doc_ids` (paper_id đúng) từ chính corpus clean; `retrieval_hit_rate` so khớp top-k tài liệu lấy về với các ID này, còn `mean_token_f1`/LLM judge so khớp câu trả lời sinh ra với `ground_truth` text — cùng một test set này được tái sử dụng cho cả baseline, corrupted và repaired.
3. Freshness monitoring chỉ đo một chiều dữ liệu (tuổi bản ghi qua `age_days`/`published`), nằm trong bước `observability/quality.py::build_freshness_report`. Quality checks khác (`row_count`, `paper_id_not_null`, `paper_id_unique`, `title_not_null`, `summary_min_length`) đo các chiều completeness/validity/uniqueness khác, chạy cùng lúc trong `run_data_quality_checks` — cả hai đều nằm sau bước cleaning và trước/sau corruption, dùng để giải thích tại sao metric của agent thay đổi.
4. Phải dùng cùng test set cho baseline/corrupted/repaired vì mục tiêu là đo ảnh hưởng của **thay đổi dữ liệu**, không phải thay đổi độ khó của câu hỏi; nếu đổi test set giữa các lần chạy, chênh lệch metric có thể do câu hỏi khác nhau chứ không phải do corruption/repair.
5. Repair được coi là thành công khi cả hai lớp bằng chứng đồng thời cải thiện: (a) quality/freshness JSON chuyển từ `success: false` (corrupted, 3/6 check fail, 36 dòng stale) về `success: true` (repaired, 6/6 pass, 0 dòng stale); và (b) các metric trong `repaired_metrics.json` (retrieval_hit_rate, mean_token_f1, judge_accuracy, mean_judge_score) phục hồi về mức tương đương hoặc tốt hơn baseline trong `corruption_report.md`.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |     1.00 |      0.83 |     1.00 | Giảm 0.1667 khi corrupt, phục hồi hoàn toàn sau repair |
| `mean_token_f1`      |     0.38 |      0.26 |     0.42 | Giảm mạnh nhất theo tỷ lệ tương đối khi corrupt, phục hồi và nhích cao hơn baseline sau repair |
| `judge_accuracy`     |    0.625 |      0.50 |     0.667 | Giảm 0.125 khi corrupt, phục hồi và nhích cao hơn baseline sau repair |
| `mean_judge_score`   |     3.58 |      3.08 |     3.71 | Giảm ~0.5 điểm/5 khi corrupt, phục hồi và nhích cao hơn baseline sau repair |
| Quality checks (pass/total) | 6/6 | 3/6 (fail: `paper_id_unique`, `summary_min_length`, `freshness_threshold`) | 6/6 | Corrupt vi phạm đúng 3 dimension bị tác động trực tiếp bởi duplicate/blank-noise/stale |
| Freshness status       | Fresh (0/50 stale) | Stale (36/65 stale) | Fresh (0/100 stale) | Freshness phục hồi hoàn toàn cùng lúc với quality |

### Kết luận từ số liệu

1. Corruption (drop + blank/noise summary + stale date + duplicate paper_id) → quality checks fail đúng 3/6 (`paper_id_unique`, `summary_min_length`, `freshness_threshold`), freshness chuyển Fresh→Stale (36/65 dòng) → retrieval_hit_rate giảm 1.00→0.83 và mean_token_f1 giảm 0.38→0.26 (nội dung/summary hỏng làm sai lệch cả retrieval và câu trả lời).
2. Repair (rebuild lại từ `raw_records_json` gốc, không sửa trực tiếp bản corrupted) → quality/freshness về PASS/Fresh hoàn toàn (6/6 check, 0 dòng stale) → agent metric phục hồi về mức bằng hoặc cao hơn baseline (`judge_accuracy` 0.625→0.667, `mean_token_f1` 0.38→0.42), cho thấy repair khôi phục dữ liệu từ nguồn tin cậy thực sự sửa được vấn đề gốc, không chỉ che dấu hiệu lỗi.

Corruption nào ảnh hưởng rõ nhất và vì sao?

Kết hợp blank/noise summary + stale date là rõ nhất, vì cả hai đều tác động trực tiếp vào nội dung dùng để embedding (`text_for_embedding` chứa summary) và vào field dùng để tính freshness — đây là nguyên nhân trực tiếp kéo `mean_token_f1` giảm tương đối nhiều nhất (~32%) trong khi `retrieval_hit_rate` giảm ít hơn (~17%) vì top-k=6 vẫn đủ rộng để bù một phần các tài liệu bị duplicate/stale.

Kết quả nào khác với kỳ vọng ban đầu?

Kỳ vọng ban đầu là repaired metric sẽ **bằng đúng** baseline (vì repair dùng lại đúng raw source). Thực tế repaired hơi **cao hơn** baseline ở `mean_token_f1`, `judge_accuracy`, `mean_judge_score`. Giả thuyết: `repaired.json` có `total_rows = 100` trong khi `baseline.json` chỉ có `total_rows = 50` (xem `data/quality/baseline.json` và `data/quality/repaired.json`), tức `raw_records_json` đã có nhiều bản ghi hơn tại thời điểm chạy repair so với snapshot dùng để tạo baseline ban đầu — corpus lớn hơn có thể cho retrieval/judge context tốt hơn một chút. Đây là giả thuyết dựa trên đối chiếu artifact, chưa chạy lại thực nghiệm để cố định số dòng và kiểm chứng riêng phần đóng góp của kích thước corpus.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Một pipeline nhiều bước phụ thuộc API ngoài (OpenAI) cần graceful degradation (fallback cố định dimension) chứ không chỉ retry/crash, nếu không một lỗi mạng tạm thời sẽ làm mất toàn bộ artifact so sánh của buổi chạy.
2. Quality checks và freshness là hai tín hiệu observability tách biệt nhưng bổ sung nhau: freshness chỉ nói được "dữ liệu cũ hay mới", còn quality checks mới chỉ ra chính xác dimension nào (uniqueness, completeness...) bị vi phạm để lần ra corruption cụ thể.
3. Corruption ở tầng nội dung (blank/noise summary) tác động agent metric mạnh hơn corruption ở tầng cấu trúc (duplicate id) trong lab này, vì embedding/answer đều phụ thuộc trực tiếp vào text — nên khi debug agent trả lời sai, nên kiểm tra data quality trước khi nghi ngờ retrieval/LLM.

### Nếu có thêm thời gian

Cố định số dòng `raw_records_json` (snapshot theo timestamp) trước khi chạy `corruption_flow.py`, để baseline và repaired luôn cùng kích thước corpus; đo lại `repaired_metrics.json` sau khi cố định để xác nhận chênh lệch hiện tại (mục 8) là do corpus size hay do biến động ngẫu nhiên của LLM judge.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Mai Thanh Trúc
**Ngày xác nhận:** 2026-08-06
