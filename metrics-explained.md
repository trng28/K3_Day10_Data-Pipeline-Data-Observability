# Giải thích các metric đánh giá RAG pipeline

Nguồn tính toán: `src/evaluation/metrics.py` (hàm `evaluate_pipeline`). Các giá trị này được ghi vào
`data/results/{baseline,corrupted,repaired}_metrics.json` và hiển thị lại trong `data/reports/*.md`
và dashboard `frontend/src/App.tsx`.

## 1. `samples`

Số câu hỏi trong test set (`data/eval/test_set.json`) đã được chạy qua pipeline để đánh giá.
Không phải một "chất lượng" mà chỉ là kích thước mẫu — dùng để hiểu độ tin cậy của các tỷ lệ bên dưới
(mẫu nhỏ thì tỷ lệ dao động mạnh giữa các lần chạy).

## 2. `retrieval_hit_rate`

```python
retrieval_hit = any(doc_id in item["ground_truth_doc_ids"] for doc_id in result.retrieved_doc_ids)
retrieval_hit_rate = mean(1.0 if item["retrieval_hit"] else 0.0 for item in answers)
```

- Với mỗi câu hỏi, hệ thống lấy về `top_k` tài liệu (`TOP_K`, mặc định 4) bằng semantic search.
- Nếu **ít nhất một** trong các tài liệu lấy về khớp với `ground_truth_doc_ids` (tài liệu đúng được
  gán sẵn khi tạo test set) → tính là 1 "hit" cho câu hỏi đó.
- `retrieval_hit_rate` = trung bình số hit trên tổng số câu hỏi → luôn nằm trong **[0.0, 1.0]**
  (0% đến 100%). Đây là chỉ số recall@k ở mức tài liệu, không quan tâm câu trả lời cuối cùng đúng
  hay sai — chỉ đo "index có tìm đúng tài liệu không".

## 3. `mean_token_f1`

```python
precision = overlap / len(pred_tokens)
recall = overlap / len(ref_tokens)
f1 = 2 * precision * recall / (precision + recall)
```

- So khớp tập token (đã lowercase, tách theo whitespace) giữa câu trả lời dự đoán và câu trả lời
  tham chiếu (`ground_truth`).
- F1 trung bình trên toàn bộ test set, cũng nằm trong **[0.0, 1.0]**. Đây là một proxy rẻ, không
  cần LLM, để đo "câu trả lời có dùng đúng từ khóa với đáp án mẫu không" — không đánh giá được ngữ
  nghĩa/diễn đạt khác từ.

## 4. `judge_accuracy` và `mean_judge_score`

- LLM (theo `LLM_PROVIDER`/`LLM_MODEL`) được yêu cầu trả về structured output `JudgeVerdict`:
  - `score`: 1–5
  - `correct`: bool ("đúng về nội dung" hay không)
  - `reasoning`: giải thích ngắn
- `judge_accuracy` = tỷ lệ câu có `correct = true` → nằm trong **[0.0, 1.0]**.
- `mean_judge_score` = điểm trung bình 1–5 (không phải tỷ lệ %, thang đo riêng).
- **Fallback**: nếu lời gọi LLM lỗi (hết quota, mất mạng, model không hỗ trợ structured output…),
  hệ thống chuyển sang heuristic dựa trên `token_f1`:
  `f1 >= 0.95 → score 5`, `f1 >= 0.5 → score 3`, còn lại `score 1`; `correct = score >= 3`.

## 5. `ragas` (tuỳ chọn)

- Mặc định bị skip (`{"skipped": "Set RUN_RAGAS=1 ..."}`) vì chạy chậm và cần thêm lượt gọi LLM.
- Khi `RUN_RAGAS=1`, chạy 4 metric của thư viện Ragas: `answer_relevancy`, `context_precision`,
  `context_recall`, `faithfulness` — tất cả đều là tỷ lệ trong **[0.0, 1.0]**.

## 6. Cách đọc bảng so sánh baseline / corrupted / repaired

`generate_corruption_report` (`src/observability/reporting.py`) in thêm cột **delta** =
`current - baseline` cho từng metric. Vì mọi metric ở trên (trừ `mean_judge_score`, thang 1–5) đều
là tỷ lệ 0–1, delta hợp lệ luôn nằm trong khoảng **[-1.0, +1.0]**. Nếu bất kỳ giá trị nào hiển thị
vượt ngoài khoảng 0–1 (hoặc ngoài 0–100 khi đã đổi sang %), đó là dấu hiệu bug ở tầng hiển thị
(nhân % hai lần, đọc sai field, hoặc dữ liệu đầu vào bị hỏng) — không phải hành vi của
`evaluate_pipeline`.
