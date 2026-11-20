# Tên đề tài:

Phân tích nhu cầu tuyển dụng và khám phá các nhóm kỹ năng IT tại Việt Nam, bao gồm thực tập sinh và mọi cấp bậc kinh nghiệm.

# `clean_data_processed.csv`

Là bản bổ sung đặc trưng phục vụ phân tích từ `clean_data.csv`

3.135 dòng, 65 cột. Trong tập 2.869 tin IT sơ bộ:

| Dữ liệu có thể tận dụng                |   Số tin |
| -------------------------------------- | -------: |
| Có JD                                  |    2.843 |
| Được gắn nhãn Intern / Fresher         | 92 / 130 |
| Có ít nhất một ngoại ngữ được ghi nhận |    1.552 |
| Có ít nhất một quyền lợi được ghi nhận |    2.197 |
| Đủ hai cận lương để phân tích          |      688 |
| Xác định được hình thức làm việc       |      745 |

| Nội dung               | `clean_data.csv` ban đầu              | `clean_data_processed.csv`                                                            |
| ---------------------- | ------------------------------------- | ------------------------------------------------------------------------------------- |
| **Số dòng**            | 3.204                                 | Dự kiến **3.135**, sau khi bỏ 69 bản ghi phụ                                          |
| **Phạm vi IT**         | Có `it_decision`                      | Thêm `scope_status` để phân biệt tin dùng sơ bộ và tin chờ rà soát                    |
| **Lương**              | Min, max, trung bình đã là VNĐ        | **Giữ nguyên giá trị**, thêm cờ kiểm tra và điều kiện chọn mẫu phân tích              |
| **Địa điểm**           | Có `city`, `cities`                   | Thêm `cities_clean`, `n_cities` để giữ đúng tin tuyển nhiều nơi                       |
| **Hình thức làm việc** | Có giá trị thiếu                      | Thêm `work_mode_clean`, ghi thiếu thành `Unknown`                                     |
| **Kinh nghiệm**        | Có hai cận số năm                     | Thêm cờ kiểm tra và `experience_group` để thống kê                                    |
| **Cấp bậc**            | Có `seniority`, `is_intern`           | Thêm `seniority_clean`, tách Intern và nhận diện một số cách ghi nhiều cấp bậc        |
| **JD**                 | Có `description`                      | Thêm `description_clean` và `text_for_tfidf`                                          |
| **Kỹ năng**            | `tech`, `keywords` đã được trích xuất | Thêm `skills`: chuẩn hóa một số tên, gộp và loại trùng; tách khái niệm chung/lĩnh vực |

## Ví dụ:

Một tin ban đầu có:

    tech:     ["Python", "SQL"]
    keywords: ["SQL", "AWS", "Cloud", "Fintech"]

Sau xử lý, vẫn giữ hai cột gốc và có thêm:

    skills:               ["AWS", "Python", "SQL"]
    broad_concepts:       ["Cloud"]
    application_domains:  ["Fintech"]
    n_skills:              3

### ==> Giá trị chính của `clean_data_processed.csv` là có sẵn các đặc trưng và cờ lựa chọn dữ liệu, giúp bước EDA, gom cụm và luật kết hợp không phải xử lý lại từ đầu.

# Tổng quan bước 2.1 — Kiểm tra và chuẩn bị dữ liệu

Notebook sử dụng `clean_data.csv` đã được tiền xử lý trước đó, tiếp tục kiểm tra chất lượng và bổ sung các đặc trưng phục vụ EDA, gom cụm, luật kết hợp và phân lớp.

**Đầu vào:** `clean_data.csv`  
**Đầu ra:** `clean_data_processed.csv`

### 2.1.1 — Đọc và khảo sát dữ liệu

Xem cấu trúc bảng, dữ liệu thiếu, các dạng trùng và những nhãn quan trọng. Mục đích là hiểu dữ liệu đang có trước khi quyết định xử lý; chưa xóa các dòng chỉ vì thiếu thông tin.

### 2.1.2 — Xử lý tin trùng và kiểm tra phạm vi IT

- **Mục 1–3:** Kiểm tra các nhóm tin trùng và chọn một bản ghi đại diện cho mỗi nhóm, tránh đếm nhiều lần cùng một tin.

- **Mục 4–6:** Kiểm tra nhãn phạm vi IT, tạo danh sách cần rà soát và tập IT dùng sơ bộ. Tin chưa rõ phạm vi vẫn được giữ trong bảng chính.

### 2.1.3 — Kiểm tra và xử lý dữ liệu lương

- **Mục 1–4:** Kiểm tra kiểu số, tính hợp lệ của hai cận và sự nhất quán giữa nhãn lương với dữ liệu số. Các cột min, max, trung bình đã là VNĐ nên không quy đổi hoặc tính lại.

- **Mục 5–6:** Gắn cờ giả định về chu kỳ lương và chọn các tin đủ điều kiện phân tích. Tin thiếu lương vẫn được giữ để phân tích kỹ năng.

### 2.1.4 — Chuẩn hóa địa điểm, kinh nghiệm và cấp bậc

- **Mục 1–2:** Chuyển địa điểm thành danh sách, giữ đầy đủ tin tuyển nhiều nơi và tách hình thức làm việc Remote/Hybrid/Onsite khỏi tỉnh, thành phố.

- **Mục 3–4:** Kiểm tra khoảng kinh nghiệm và tạo nhóm theo số năm tối thiểu được yêu cầu; không coi kinh nghiệm thiếu là 0 năm.

- **Mục 5–6:** Tách Intern, nhận diện một số tiêu đề tuyển nhiều cấp bậc và lưu nguồn xác định nhãn để phân biệt thông tin ghi rõ với thông tin suy đoán.

### 2.1.5 — Làm sạch JD và chuẩn hóa kỹ năng

- **Mục 1–5:** Làm sạch văn bản JD, chuẩn hóa và gộp kỹ năng đã có trong `tech`, `keywords`; tách khái niệm chung và lĩnh vực ứng dụng. Tạo thêm nhánh văn bản bỏ stop words để dùng khi cần.

- **Mục 6–8:** Cập nhật các bảng, tạo ma trận kỹ năng 0/1 và đối chiếu mẫu với JD để phát hiện kỹ năng nhận nhầm hoặc bỏ sót.

### 2.1.6 — Kiểm tra tổng thể và lưu dữ liệu

- **Mục 1–4:** Kiểm tra mã tin, thông tin truy vết, danh sách kỹ năng và sự khớp nhau giữa các bảng; tổng kết chất lượng dữ liệu.

- **Mục 5–6:** Lưu một file `clean_data_processed.csv`, sau đó đọc lại để kiểm tra thông tin được bảo toàn. Các bảng con và ma trận có thể tạo lại từ file này.

> **Lưu ý:** Kết quả hiện phục vụ phân tích sơ bộ. Các tin chưa rõ phạm vi và chất lượng trích xuất kỹ năng vẫn cần rà soát; nhãn “đã xử lý” không đồng nghĩa mọi thông tin đã được xác minh.

# Ba hướng mở rộng đề xuất

| Hướng mở rộng                            | Câu hỏi cần trả lời                                                                                                             | Kết quả có thể trình bày                                                  |
| ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| **Bộ kỹ năng cho người mới vào nghề**    | Trong từng nhóm nghề, Intern/Fresher thường được nhắc tới những kỹ năng nào? Khác Junior/Middle/Senior ở đâu?                   | Heatmap kỹ năng × cấp bậc; bảng các bộ kỹ năng thường xuất hiện cùng nhau |
| **Chân dung tuyển dụng ngoài mức lương** | Các nhóm kỹ năng/cụm tuyển dụng khác nhau thế nào về ngoại ngữ, đào tạo, bảo hiểm, thưởng và hình thức làm việc?                | Bảng chân dung cụm gồm kỹ năng, cấp bậc, ngoại ngữ và quyền lợi           |
| **Kiểm tra độ vững của kết luận**        | Một kỹ năng phổ biến vì nhiều công ty cùng tuyển, hay vì vài đơn vị đăng nhiều tin? Kết quả có giống nhau giữa các nguồn không? | So sánh Top kỹ năng theo số tin, số đơn vị đề cập và từng nền tảng        |

Ba hướng này nối trực tiếp vào quy trình hiện tại:

- 2.2: thêm góc nhìn theo cấp bậc, ngoại ngữ và quyền lợi.
- 2.3: mô tả cụm bằng nhiều đặc điểm thực tế hơn.
- 2.4: dùng luật kết hợp để bổ sung các bộ kỹ năng cho từng nhóm nghề.
- 2.5: có thêm thông tin để lựa chọn đặc trưng và giải thích kết quả.

Ví dụ, sau gom cụm, thay vì chỉ nói “cụm này có Python, SQL, Spark”, nhóm có thể mô tả:
Cụm này tập trung vào những công nghệ nào, thường đi với cấp bậc nào, có đề cập ngoại ngữ và đào tạo ra sao, số tin và số đơn vị đăng tuyển là bao nhiêu.
