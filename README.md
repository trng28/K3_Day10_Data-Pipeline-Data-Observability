# Day 10 - Data Pipeline & Data Observability

## Local observability demo (React + TypeScript)

The demo runs the existing Python scripts, edits safe flow settings in `.env`, and compares
baseline, corrupted, and repaired artifacts.

```powershell
cd frontend
npm install
npm run build
cd ..
.\.venv\Scripts\python.exe demo\server.py
```

Open `http://127.0.0.1:8787`. For frontend development, keep the Python server running and use
`npm run dev` from `frontend/`, then open `http://127.0.0.1:5173`.

## Mục tiêu bài lab

Bài lab mô phỏng quy trình xây dựng và vận hành data pipeline cho một hệ thống RAG sử dụng dữ liệu bài báo học thuật từ Crossref.

Học viên sẽ thực hiện toàn bộ vòng đời dữ liệu:

- Lấy dữ liệu từ nguồn bên ngoài và lưu lại raw artifacts để có thể truy vết.
- Làm sạch, chuẩn hóa và chuyển dữ liệu sang schema phù hợp cho embedding.
- Tạo embedding, nạp dữ liệu vào ChromaDB và dùng corpus này để trả lời câu hỏi.
- Xây evaluation set và đo chất lượng retrieval/câu trả lời trên dữ liệu sạch.
- Chủ động tạo các lỗi dữ liệu như thiếu bản ghi, summary rỗng, text nhiễu, ngày cũ và duplicate.
- Đo ảnh hưởng của dữ liệu lỗi lên chất lượng agent bằng cùng một evaluation set.
- Repair dữ liệu từ nguồn raw, chạy đánh giá lại và so sánh ba trạng thái: baseline, corrupted và repaired.
- Tạo data quality report, freshness report và báo cáo so sánh để phát hiện vấn đề trước khi người dùng nhận câu trả lời sai.

Trọng tâm của bài không chỉ là làm cho ETL chạy được. Học viên phải **chứng minh bằng artifact và metrics rằng chất lượng dữ liệu ảnh hưởng trực tiếp đến chất lượng của RAG/agent**, đồng thời cho thấy pipeline có thể phát hiện và phục hồi sau lỗi dữ liệu.

## Luồng thực hiện và đầu ra

Pipeline hoàn chỉnh đi theo luồng:

```text
Crossref API
    -> raw data
    -> cleaned data
    -> embedding + ChromaDB
    -> RAG evaluation
    -> quality/freshness reports
    -> corrupt data
    -> evaluate impact
    -> repair from raw data
    -> compare baseline/corrupted/repaired
```

Kết thúc bài lab, học viên cần có:

- Baseline pipeline chạy end-to-end trên dữ liệu sạch.
- Corruption flow tạo được dữ liệu lỗi có chủ đích.
- Repaired pipeline phục hồi dữ liệu và chạy đánh giá lại.
- Metrics và câu trả lời của agent ở cả ba trạng thái để đối chiếu.
- Data quality, freshness và comparison reports trong `data/`.

Xem yêu cầu chi tiết tại:

- [Hướng dẫn từng bước](Guide.md)
- [Rubric chấm điểm](Rubric.md)

## 1. Yêu cầu trước khi bắt đầu

- **Python 3.11, 3.12 hoặc 3.13** (theo `pyproject.toml` và `uv.lock`)
- Khuyến nghị dùng [uv](https://docs.astral.sh/uv/getting-started/installation/) để cài đúng dependency từ lockfile
- Internet để lấy dữ liệu từ Crossref và tải embedding model lần đầu
- API key của ít nhất một LLM provider nếu chạy các bước có gọi LLM

Nếu máy có nhiều phiên bản Python, hãy chọn Python trong khoảng 3.11-3.13 trước khi cài dependency.

## 2. Cài môi trường

### Cách A - Dùng uv (khuyến nghị)

Tại thư mục gốc của project:

```bash
uv sync
```

`uv sync` tạo môi trường `.venv`, cài project và dependency theo `uv.lock`.

### Cách B - Dùng pip

Tạo và kích hoạt virtual environment.

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

> Không chỉ chạy `pip install -r requirements.txt`: lệnh đó cài các thư viện nhưng không cài package nằm trong `src/`.  ` cài cả project và dependency cần thiết.

## 3. Cấu hình `.env`

Tạo `.env` từ file mẫu.

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

macOS/Linux:

```bash
cp .env.example .env
```

Mặc định project dùng Gemini:

```dotenv
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.5-flash
GOOGLE_API_KEY=your_key_here
```

Project cũng hỗ trợ `openai`, `anthropic`, `openrouter`, `ollama` và OpenAI-compatible custom endpoint. Chỉ điền credential của provider bạn sử dụng.

Không commit `.env`, API key hoặc secret lên GitHub.

## 4. Hiểu starter trước khi code

Các thư mục chính:

| Thư mục              | Chức năng                                       |
| ---------------------- | ------------------------------------------------- |
| `src/core/`          | Cấu hình, đường dẫn và utility dùng chung |
| `src/ingestion/`     | Lấy dữ liệu Crossref, cleaning và corruption  |
| `src/retrieval/`     | Embedding, ChromaDB, LLM providers và agent      |
| `src/evaluation/`    | Tạo test set và tính metrics                   |
| `src/observability/` | Data quality, freshness và báo cáo             |
| `src/pipelines/`     | Điều phối baseline flow và corruption flow    |
| `script/`            | Hai entrypoint để chạy pipeline                |
| `data/`              | Artifact sinh ra khi chạy lab                    |

Starter cố ý chứa `TODO(student)` và `NotImplementedError`. Đây là trạng thái mong đợi, không phải lỗi setup.

Tìm tất cả phần cần hoàn thành:

```bash
rg -n "TODO\(student\)|NotImplementedError" src
```

Nếu chưa cài `rg`, dùng một trong các lệnh sau.

Windows PowerShell:

```powershell
Get-ChildItem src -Recurse -Filter *.py | Select-String -Pattern 'TODO\(student\)|NotImplementedError'
```

macOS/Linux:

```bash
grep -RInE 'TODO\(student\)|NotImplementedError' src
```

Hoặc dùng chức năng Search của VS Code với từ khóa `TODO(student)`.

## 5. Thứ tự thực hiện

### Pha 1 - Baseline với dữ liệu sạch

1. Implement Crossref ingestion trong `src/ingestion/crossref.py`.
2. Implement cleaning trong `src/ingestion/cleaning.py`.
3. Tạo evaluation set trong `src/evaluation/testset.py`.
4. Implement quality/freshness checks và report trong `src/observability/`.
5. Ghép các bước trong `src/pipelines/phase1.py`.
6. Chạy baseline:

```bash
uv run python script/run_phase1.py
```

Nếu dùng pip và đã kích hoạt `.venv`:

```bash
python script/run_phase1.py
```

### Pha 2 - Corruption, repair và comparison

Chỉ bắt đầu pha này sau khi baseline chạy thành công.

1. Implement corruption trong `src/ingestion/corruption.py`.
2. Ghép corruption, evaluation, repair và comparison trong `src/pipelines/corruption_flow.py`.
3. Chạy flow:

```bash
uv run python script/run_corruption_flow.py
```

Nếu dùng pip:

```bash
python script/run_corruption_flow.py
```

## 6. Kiểm tra kết quả

Sau baseline, tối thiểu cần kiểm tra:

- `data/raw/`: raw response và records từ Crossref
- `data/clean/`: cleaned CSV/JSON
- `data/embeddings/`: embedding manifest
- `data/eval/`: evaluation test set
- `data/results/baseline_metrics.json`: metrics của baseline
- `data/quality/`: data quality và freshness report
- `data/reports/phase1_report.md`: báo cáo baseline

Sau corruption flow, kiểm tra thêm:

- corrupted/repaired dataset và metrics trong `data/`
- `data/results/corruption_log.json`
- `data/reports/corruption_report.md`

Các chỉ số trọng tâm:

- `retrieval_hit_rate`
- `mean_token_f1`
- `judge_accuracy`
- `mean_judge_score`
- trạng thái data quality và freshness

Mục tiêu không chỉ là pipeline chạy xong, mà phải có bằng chứng cho thấy data corruption làm thay đổi chất lượng agent và repair giúp khôi phục chất lượng.

## 7. Ý nghĩa của project, những gì được chứng minh và cách điều chỉnh chỉ số

### 7.1. Vì sao bài lab này quan trọng

Trong một hệ thống RAG thật, khi corpus bị lỗi (thiếu bản ghi, dữ liệu cũ, text nhiễu, trùng lặp),
hệ thống **không sập** — nó vẫn trả lời, chỉ là trả lời sai hoặc thiếu, và người dùng thường là
người phát hiện ra đầu tiên. Bài lab này mô phỏng đúng rủi ro đó trong môi trường có kiểm soát, để
học viên xây dựng năng lực: (1) đo được chất lượng dữ liệu độc lập với chất lượng model, (2) đo
được tác động của dữ liệu lỗi lên output cuối, và (3) chứng minh pipeline có khả năng phục hồi.

### 7.2. Project chứng minh điều gì

Thiết kế thí nghiệm giữ **cố định** mọi thứ trừ corpus: cùng một `test_set.json`, cùng logic
retrieval/answer, cùng LLM/judge. Chỉ dữ liệu thay đổi qua 3 trạng thái `baseline -> corrupted ->
repaired`. Vì mọi biến khác được giữ nguyên, mọi thay đổi ở metrics chỉ có thể quy về một nguyên
nhân: chất lượng dữ liệu đầu vào. Kết quả trong `data/reports/corruption_report.md` do đó chứng
minh được ba việc:

- **Chất lượng dữ liệu tác động trực tiếp đến chất lượng RAG/agent** — không phải giả thuyết, mà có
  số liệu delta cụ thể giữa baseline và corrupted.
- **Data quality/freshness checks phát hiện lỗi trước khi cần chạy lại toàn bộ agent** — các check
  này chạy trên `DataFrame` thô, không cần gọi LLM, nên phát hiện sớm và rẻ hơn nhiều so với việc
  chờ agent trả lời sai rồi mới biết.
- **Pipeline có thể phục hồi** — repair từ `raw_records_json` (không phải từ dữ liệu đã bị corrupt)
  đưa metrics trở lại gần mức baseline, chứng minh lỗi không phải là vĩnh viễn nếu raw data còn giữ được.

### 7.3. Các chỉ số phản ánh điều gì

Chi tiết công thức từng chỉ số nằm ở [metrics-explained.md](metrics-explained.md); tổng quan vai
trò của mỗi nhóm chỉ số trong việc "chứng minh" ở trên:

| Nhóm chỉ số | Chỉ số | Phản ánh điều gì |
| --- | --- | --- |
| Observability (rẻ, không cần LLM) | Data quality checks (`row_count`, `paper_id_not_null`, `paper_id_unique`, `title_not_null`, `summary_min_length`, `freshness_threshold`) | Tính đúng đắn cấu trúc/schema của dữ liệu — phát hiện lỗi *trước* khi nó lan tới người dùng |
| Observability (rẻ, không cần LLM) | Freshness report (`stale_rows`, `invalid_date_rows`, `is_fresh`) | Dữ liệu có còn "mới" so với ngưỡng `FRESHNESS_THRESHOLD_DAYS` hay không — một tín hiệu quản trị dữ liệu độc lập với việc câu trả lời đúng/sai |
| Kết quả cuối (đắt hơn, cần LLM/agent) | `retrieval_hit_rate` | Embedding/ChromaDB có tìm đúng tài liệu nguồn hay không — đo tầng retrieval, tách biệt với tầng sinh câu trả lời |
| Kết quả cuối (đắt hơn, cần LLM/agent) | `mean_token_f1` | Câu trả lời có dùng đúng từ khóa với đáp án mẫu không — proxy rẻ, không cần LLM judge |
| Kết quả cuối (đắt hơn, cần LLM/agent) | `judge_accuracy`, `mean_judge_score` | Đánh giá ngữ nghĩa của câu trả lời bởi một LLM judge độc lập — gần với "trải nghiệm người dùng thật" nhất |

Ý nghĩa quan trọng nhất: **hai nhóm chỉ số đo hai tầng khác nhau của cùng một lỗi**. Data
quality/freshness là *leading indicator* (cảnh báo sớm ở tầng dữ liệu), còn retrieval/F1/judge là
*lagging indicator* (đo hậu quả thực tế ở tầng câu trả lời). Một pipeline observability tốt cần cả
hai — chỉ nhìn leading indicator có thể bỏ lỡ lỗi logic ở tầng retrieval/answer; chỉ nhìn lagging
indicator thì phát hiện lỗi quá muộn (sau khi agent đã trả lời sai).

### 7.4. Điều chỉnh để chứng minh rõ hơn hoặc kiểm định độ nhạy

Các biến điều chỉnh được trong `.env` (hoặc qua panel cấu hình của dashboard demo):

- `CORRUPTION_DROP_RATE`, `CORRUPTION_BLANK_RATE`, `CORRUPTION_NOISE_RATE`,
  `CORRUPTION_STALE_RATE`, `CORRUPTION_DUPLICATE_RATE` (mặc định 0.08-0.12): tăng các giá trị này
  (tối đa 0.5) để corruption ảnh hưởng rõ rệt hơn lên metrics — hữu ích khi muốn chứng minh delta
  lớn hơn giữa baseline và corrupted. Giảm về gần 0 nếu muốn kiểm tra pipeline có "quá nhạy" hay
  không (metrics giảm ngay cả khi lỗi rất nhỏ là dấu hiệu retrieval/answer logic thiếu robust).
- `FRESHNESS_THRESHOLD_DAYS` (mặc định 180): hạ ngưỡng này để data quality/freshness check trở nên
  khắt khe hơn — dùng để kiểm tra xem check có thực sự bắt được dữ liệu cũ hay không.
- `TOP_K` (mặc định 4): tăng để xem `retrieval_hit_rate` có "dễ đạt 100%" hơn không (top-k lớn hơn
  = dễ trúng hơn); giảm để kiểm định retrieval có thực sự chính xác ở top-1/top-2.
- `REFRESH_TEST_SET=1`: bắt buộc tạo lại `test_set.json` từ corpus hiện tại — cần làm khi corpus đã
  đổi nhiều (ví dụ sau khi crawl lại) để câu hỏi eval luôn tham chiếu tài liệu còn tồn tại trong
  corpus, tránh false negative do câu hỏi trỏ tới tài liệu đã không còn trong dữ liệu mới.
- `RUN_RAGAS=1`: bật thêm 4 metric của Ragas (`answer_relevancy`, `context_precision`,
  `context_recall`, `faithfulness`) để có góc nhìn đánh giá sâu hơn, đổi lại thời gian chạy lâu hơn
  vì cần thêm lượt gọi LLM cho mỗi câu hỏi.

Sau khi đổi bất kỳ biến nào ở trên, chạy lại `script/run_phase1.py` rồi `script/run_corruption_flow.py`
để các report/metrics phản ánh đúng cấu hình mới.

## 8. Lỗi setup thường gặp

| Triệu chứng                                         | Nguyên nhân thường gặp                          | Cách kiểm tra/xử lý                                                             |
| ----------------------------------------------------- | ---------------------------------------------------- | ----------------------------------------------------------------------------------- |
| `requires a different Python`                       | Python nằm ngoài khoảng 3.11-3.13                 | Chạy`python --version`, chọn Python phù hợp rồi tạo lại `.venv`          |
| `No module named 'pipelines'`                       | Mới cài`requirements.txt`, chưa cài project    | Trong`.venv`, chạy `python -m pip install -e .`                                |
| `GOOGLE_API_KEY is required`                        | Provider mặc định là Gemini nhưng chưa có key | Điền`GOOGLE_API_KEY` hoặc đổi `LLM_PROVIDER` sang provider đã cấu hình |
| `NotImplementedError: Student task...`              | Chạm tới phần starter chưa implement             | Mở đúng file được ghi trong traceback và hoàn thành`TODO(student)`       |
| Crossref trả`429`/`503`                          | Rate limit hoặc lỗi tạm thời                     | Implement retry/backoff theo yêu cầu trong`src/ingestion/crossref.py`           |
| Chạy corruption flow nhưng thiếu baseline artifact | Chưa chạy xong Pha 1                               | Chạy baseline và kiểm tra`data/results/baseline_metrics.json` trước          |

## 9. Checklist trước khi nộp

- [ ] Cài đặt được trên môi trường sạch bằng một trong hai cách ở trên
- [ ] Baseline pipeline chạy end-to-end
- [ ] Corruption flow chạy sau baseline
- [ ] Có đầy đủ raw, clean, embedding, evaluation, quality và report artifacts
- [ ] Metrics/report khớp với artifact thực tế
- [ ] Chứng minh được before/corrupted/repaired bằng số liệu
- [ ] Không có API key hoặc `.env` trong Git
- [ ] Đã đối chiếu [Rubric.md](Rubric.md)
