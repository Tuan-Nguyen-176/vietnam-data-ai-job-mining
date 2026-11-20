# Cách nhóm làm sạch dữ liệu tuyển dụng IT

Năm website trả về dữ liệu theo năm kiểu khác nhau. Cùng một việc có thể được đăng lại, tìm “IT” có thể ra tin tuyển nhân sự, còn “15–20 triệu” có thể thiếu kỳ trả. Nếu đưa thẳng các dòng đó vào phân tích, nhóm sẽ đếm dư việc, tính sai lương hoặc gắn nhầm kỹ năng. Đó là ý nghĩa của **rác vào → rác ra** trong bài này.

Pipeline bỏ trùng và lọc phạm vi trước khi tải mô tả công việc (**JD**). Sau đó nó chuẩn hóa lương, kỹ năng và các trường khác. Những dữ liệu chưa biết được giữ trống hoặc gắn trạng thái để còn kiểm tra. Hai bảng cuối nối với nhau bằng `job_uid`, có `URL_Goc` và `Timestamp` để nhóm mở lại tin gốc và biết thời điểm thu thập.

- [Thứ tự chạy và điểm dừng](#thứ-tự-chạy-và-điểm-dừng)
- [Giải thích từng file và từng hàm](#giải-thích-từng-file-và-từng-hàm)
- [Cách lấy mô tả theo từng website](#cách-lấy-mô-tả-theo-từng-website)
- [Chạy lại từ đâu khi có thay đổi](#chạy-lại-từ-đâu-khi-có-thay-đổi)

## Thứ tự chạy và điểm dừng

Chạy lệnh từ thư mục gốc của dự án. Tên thư mục trên đĩa là `pipline`. Có **5 file chạy trực tiếp** trong thư mục này và **2 file chứa hàm dùng chung**. Bước tải JD thuộc thư mục `crawler` nhưng nằm giữa quy trình.

```text
data/raw/*.jsonl
    → duplicate → data/dedup.jsonl
    → filter_it → data/it.jsonl + data/non_it.jsonl
    → crawler.fetch_detail → data/full.jsonl
         ├─ clean_salary         → data/salary.jsonl
         └─ extract_tech_skill_  → data/tech_skills.jsonl

full.jsonl + salary.jsonl + tech_skills.jsonl
    → export_data (gọi lam_sach và group_jobs)
    → duyệt data/it_review.csv → chạy lại export_data
    → raw_data.csv + clean_data.csv + data/duplicate_groups.csv
```

JSONL lưu mỗi tin trên một dòng JSON. Một **tag** là nhãn lấy trực tiếp từ thẻ tin. **Regex** là mẫu tìm văn bản, chẳng hạn nhận ra cụm “2–4 năm kinh nghiệm”. Bước tải JD cần Chrome, Playwright, Beautiful Soup, lxml và tqdm. Bước xuất CSV dùng RapidFuzz để so tên công ty và chức danh gần giống nhau.

### Bước 1 Khử trùng tin thô

```powershell
python -m pipline.duplicate
```

Đọc các file `.jsonl` ngay trong `data/raw/` và ghi `data/dedup.jsonl`. So sánh ba số in ra là số dòng ban đầu, số còn lại sau khử trùng URL và số còn lại sau khử trùng trong cùng sàn. Nếu mất nhiều tin bất thường, đối chiếu một vài cặp cùng công ty và chức danh ở các địa điểm khác nhau. Tệp demo để ở thư mục riêng sẽ tránh bị gộp vào dữ liệu chính.

### Bước 2 Lọc tin theo phạm vi IT

```powershell
python -m pipline.filter_it
```

Đọc `data/dedup.jsonl` và từ điển kỹ năng. `data/it.jsonl` chứa cả `keep` lẫn `ambiguous`, còn `data/non_it.jsonl` chứa `drop`. Dừng để xem thống kê từng nguồn và mở mẫu các tin bị loại, nhất là những tiêu đề chung như “Engineer” hoặc “Analyst”. Tin bị loại ở đây sẽ nằm ngoài đầu vào của bước tải JD và bước duyệt cuối.

### Bước 3 Bổ sung mô tả công việc

```powershell
python -m crawler.fetch_detail
```

Đọc `data/it.jsonl` và ghi `data/full.jsonl`. Nếu có tin LinkedIn cần tải, chương trình cần hồ sơ Chrome đã đăng nhập. Khi chỉ bổ sung một nguồn, ví dụ `python -m crawler.fetch_detail --site topcv --limit 5`, giới hạn 5 áp dụng cho danh sách tin cần tải của nguồn đó. File đầu ra vẫn chứa toàn bộ danh sách đầu vào, gồm kết quả cũ và các dòng chưa tải.

Dừng để mở thử vài JD và xem `data/details-errors.jsonl` nếu lần chạy có lỗi. Một JD có menu hoặc tin gợi ý sẽ làm bước trích kỹ năng đếm nhầm. Khi cần chạy tiếp, dùng lại file đầu ra đã lưu để chương trình nhận diện tin đã có JD.

### Bước 4 Chuẩn hóa lương

```powershell
python -m pipline.clean_salary
```

Đọc `data/full.jsonl` và ghi `data/salary.jsonl`. Xem số lượng theo `salary_status` và các ví dụ `unknown` được in ra. Đối chiếu vài dòng lương năm, USD hoặc chỉ có một cận với chuỗi gốc trước khi dùng cho biểu đồ.

### Bước 5 Trích kỹ năng và từ khóa

```powershell
python -m pipline.extract_tech_skill_
```

Đọc cùng bản `data/full.jsonl` và ghi `data/tech_skills.jsonl`. Xem danh sách công nghệ và từ khóa phổ biến để phát hiện từ bị bắt nhầm. Bước 4 và 5 có thể đổi thứ tự. Cả hai cần hoàn tất trên cùng một bản `full.jsonl` trước khi xuất CSV.

### Bước 6 Xuất CSV và dừng duyệt tay

```powershell
python -m pipline.export_data
```

Lần chạy đầu tạo hai CSV và cập nhật `data/it_review.csv`. Mở file duyệt, đọc `title` và `jd_dau`, dùng `job_url` khi đoạn trích chưa đủ. Điền `keep` hoặc `drop` vào `quyet_dinh` và có thể ghi lý do vào `ghi_chu`. Lưu dạng CSV UTF-8 phân cách bằng dấu phẩy, rồi đóng file trước khi chạy lại. Một ô quyết định trống nghĩa là tin vẫn chờ duyệt và có thể còn xuất hiện trong hai CSV với nhãn `ambiguous`.

Chạy lại `python -m pipline.export_data` để áp dụng quyết định vừa lưu. Kiểm tra `raw_data.csv` và `clean_data.csv` có cùng tập `job_uid`, đối chiếu vài URL với bản gốc và xem các nhóm nghi trùng trong `data/duplicate_groups.csv`. `lam_sach.py` và `group_jobs.py` được gọi trong quy trình này, còn `duplicate.py` cũng dùng `parse_cities()` từ `lam_sach.py`.

## Giải thích từng file và từng hàm

### Khử trùng với duplicate.py

**Vấn đề.** Tin xuất hiện nhiều lần làm số cơ hội việc làm và số lần nhắc đến kỹ năng bị đếm dư. Bỏ trùng sớm cũng giảm số trang chi tiết cần tải.

File xét hai lượt. Lượt đầu giữ dòng đầu tiên của mỗi URL có giá trị và bỏ dòng thiếu URL. Lượt sau so **sàn + công ty + chức danh + địa điểm**. Hai tin cùng vị trí ở Hà Nội và TP.HCM có thể là hai nhu cầu tuyển khác nhau, nên địa điểm được đưa vào khóa. Các bản trên nhiều sàn thường có URL khác nhau và sẽ được đối chiếu tại `group_jobs.py`. [Mã nguồn duplicate.py](duplicate.py)

- `norm(s)` hạ chữ thường, đổi dấu câu thành khoảng trắng và gộp khoảng trắng thừa. Hàm giữ dấu tiếng Việt. “FPT Software (HCM)!” thành “fpt software hcm”.
- `city_key(location)` gọi `parse_cities()` để nhận ra tên thành phố chuẩn. “Ho Chi Minh City” và “HCM” cùng ra `TP.HCM`. Nếu chỉ nhận ra `Khác` hoặc địa điểm trống, hàm dùng chuỗi địa điểm đã qua `norm()` làm khóa.
- `key_of(row)` ghép sàn, công ty, chức danh và khóa địa điểm. Đây là dấu hiệu tin đăng lại trong cùng sàn. Hai đợt tuyển khác nhau mà có cùng cả bốn trường vẫn có thể bị gộp.
- `richer(a, b)` chọn bản có mô tả khi chỉ một bản có. Nếu cả hai cùng có hoặc cùng thiếu mô tả, chọn bản có nhiều trường được điền hơn. Nếu hòa, giữ bản đang có. Quy tắc này áp dụng cho lượt so khóa thứ hai.
- `main()` đọc các file thô theo thứ tự tên tệp, chạy hai lượt khử trùng, in số lượng rồi ghi lại `data/dedup.jsonl`. Bước này thay đầu ra cũ bằng cách xóa tệp cũ rồi ghi tệp mới.

### Lọc phạm vi với filter_it.py

**Vấn đề.** Tiêu đề “IT Sales Executive” có chữ IT nhưng công việc chính là bán hàng. Đếm nó vào nhóm kỹ thuật sẽ làm sai cả thống kê lương lẫn kỹ năng.

File dùng tiêu đề, loại vai trò nếu nguồn cung cấp và tag kỹ năng để phân luồng trước khi tải JD. Nhóm luật phân biệt vai trò IT, chức năng ngoài IT, lập trình máy CNC/PLC và các chức danh chung. Có ba kết quả. [Mã nguồn filter_it.py](filter_it.py) · [Từ điển kỹ năng](../data/skill_dictionary.json)

- `keep` nếu chức danh thuộc nhóm IT hoặc chức danh chung có tag công nghệ đủ điều kiện.
- `ambiguous` nếu chức danh chung chưa có tag phù hợp, hoặc chỉ có tag công nghệ mà chưa rõ vai trò. Tin ITviec thiếu tín hiệu rõ cũng được giữ để xem tiếp sau khi qua các luật loại.
- `drop` nếu trúng luật chức năng ngoài IT hoặc lập trình máy. Tin ở nguồn khác ITviec cũng bị loại khi thiếu cả tín hiệu vai trò lẫn tag phù hợp.

`GENERAL_TOOLS` liệt kê các công cụ dùng ở nhiều ngành như Excel, AutoCAD và Jira. Chúng vẫn có thể xuất hiện trong cột kỹ năng, nhưng riêng một tag Excel không đủ để xác nhận tin thuộc IT.

- `normalize(text)` tạo bản dùng để so khớp bằng cách hạ chữ, bỏ dấu tiếng Việt, đổi `đ` thành `d` và gộp khoảng trắng. Nó đổi cả dấu gạch ngang dài và dấu gạch dưới để “Devops_SRE” dễ khớp theo từ.
- `load_dictionary(path, groups)` kiểm tra cấu trúc JSON, rồi ánh xạ tên và biến thể về tên chuẩn. Nếu hai kỹ năng trong các nhóm được nạp tranh cùng một biến thể đã chuẩn hóa, hàm báo lỗi. Mẫu regex ưu tiên biến thể dài và so theo biên từ để “React Native” được nhận trước “React”. Bộ lọc chỉ nạp `tech`.
- `match_skills(text, dictionary, title=False)` trả về tên chuẩn và loại kỹ năng như `language` hoặc `framework`. Với `C`, `R` và `Go`, hàm chỉ nhận chuỗi nguyên vẹn hoặc trường hợp sát từ chỉ vai trò trong tiêu đề, ví dụ “Go Engineer”.
- `role_of(title, dictionary)` xét chức năng ngoài IT trước, rồi lập trình máy, nhóm IT rõ, viết tắt IT viết hoa, tổ hợp vai trò với ngôn ngữ/framework, và cuối cùng là chức danh chung hoặc chưa rõ. Các viết tắt như `BA` và `SAP` đối chiếu trên tiêu đề gốc để giảm nhầm với “Ba Vì” và “sắp xếp”.
- `classify_row(row, dictionary)` kiểm tra kiểu dữ liệu, đếm số tag khác nhau có công nghệ ngoài `GENERAL_TOOLS`, rồi dùng `role_type` làm tín hiệu bổ sung nếu tiêu đề chưa rõ. Hàm giữ các trường sẵn có và thêm `it_decision`, `it_reason`, `title_role`, `skill_hits`. `skill_hits` đếm **tag đạt điều kiện**, một tag có nhiều kỹ năng vẫn chỉ tính một lần.
- `main()` kiểm tra đường dẫn và từ điển, tự phân loại các dòng, chuẩn bị hai file tạm và thay lần lượt hai đầu ra. Nó in thống kê theo nguồn và nhắc kiểm tra thêm nếu số tin `keep` dưới 800.

### Bổ sung JD với crawler/fetch_detail.py

**Vấn đề.** Thẻ danh sách thường chỉ có tiêu đề, tag và vài trường ngắn. Nếu lấy nhầm phần “Việc làm liên quan” vào JD, kỹ năng của một tin khác sẽ xuất hiện trong tin đang phân tích.

File lập danh sách URL cần bổ sung, chọn bộ đọc theo website và lưu tiến độ vào chính `data/full.jsonl`. Việc tải lại chỉ áp dụng với những tin chưa đạt điều kiện của `description_complete()`. Bản mô tả đã được coi là đủ có thể được dùng lại dù chạy lệnh lần nữa. [Mã nguồn fetch_detail.py](../crawler/fetch_detail.py)

#### Cách lấy mô tả theo từng website

- **ITviec.** `extract_job_posting(soup)` lấy mô tả từ JSON-LD, tức khối dữ liệu có cấu trúc kiểu `JobPosting` nằm trong HTML. Hàm đọc ngày đăng, loại việc, số tháng kinh nghiệm và trường lương nếu có. Khi thiếu mô tả, nó thử khối `section.job-content` nếu đoạn này dài từ 400 ký tự và có dấu hiệu JD. Nếu tiêu đề báo “Job expired” trong nhánh dự phòng, hàm gắn `job_expired`.
- **VietnamWorks.** `fetch_public()` thử mở mục “Xem đầy đủ”. `extract_vietnamworks(soup)` lấy nội dung theo hai tiêu đề “Mô tả công việc” và “Yêu cầu công việc”, bỏ đoạn gợi ý “Mức độ phù hợp” ngắn và ghép thêm khối phúc lợi nếu thấy. Nếu phần HTML thu được rỗng, hàm thử `extract_job_posting()`. Mô tả ở API danh sách có thể kết thúc bằng `...` hoặc thiếu các tiêu đề này.
- **TopDev.** `extract_topdev(soup)` chọn khung dài nhất trong các khung từ 400 ký tự có dấu hiệu mô tả, yêu cầu hoặc phúc lợi. Nó loại khung gợi ý việc khác, rồi dự phòng bằng `description` và `jobBenefits` trong JSON-LD hoặc `extract_generic()`. Lương chi tiết được đọc từ JSON-LD khi có.
- **TopCV.** `fetch_public()` kiểm tra mã tin trong URL sau chuyển hướng. `extract_topcv(soup)` bỏ thẻ script, style và noscript rồi giao văn bản cho `trim_topcv_text(text)`. Hàm cắt này tìm dòng “Mô tả công việc” hoặc “Job Description”, ưu tiên tìm sau “Tổng quan”, rồi dừng trước mục như “Cách thức ứng tuyển” hoặc “Việc làm liên quan”. JD dưới 300 ký tự bị báo lỗi để thử lại.
- **LinkedIn.** `linkedin_job_id(url)` lấy phần mã ở cuối URL. `linkedin_csrf(ctx)` đọc giá trị xác thực phiên mà code cần gửi kèm yêu cầu. `fetch_linkedin(ctx, row)` dùng phiên Chrome đã đăng nhập để đọc JSON từ Voyager, lấy mô tả và cập nhật tiêu đề, công ty, địa điểm, thời điểm tạo khi có. Phản hồi không thành công hoặc mô tả trống được đưa qua cơ chế thử lại.

#### Hàm dùng chung và điều phối

- `site_of(url)` nhận diện sàn từ tên miền. Kết quả được dùng khi chọn bộ đọc và khi giới hạn bằng `--site`.
- `job_posting_ldjson(soup)` tìm đối tượng `JobPosting` trong các khối JSON-LD. Nó bỏ qua khối JSON lỗi và trả về đối tượng rỗng nếu thiếu dữ liệu phù hợp.
- `salary_from_ldjson(posting)` bóc chuỗi hoặc giá trị lương, cận dưới, cận trên, tiền tệ và kỳ trả từ `baseSalary`. Việc tính về VND/tháng do `clean_salary.py` thực hiện.
- `extract_generic(soup)` thử các vùng có tên liên quan đến mô tả, rồi `article` và `main`, ưu tiên đoạn trên 200 ký tự. Nếu chưa thấy, nó lấy văn bản từ `body` khi có. Đây là phương án dự phòng, văn bản có thể còn lẫn phần ngoài JD.
- `is_cloudflare(soup)` nhận diện trang xác minh bằng tiêu đề, phần tử và các cụm chữ đặc trưng. `CloudflareDetected` là loại lỗi riêng để vòng lặp biết rằng nội dung nhận được là trang xác minh.
- `description_complete(row)` trả về sai khi JD trống. Với VietnamWorks, JD phải có ít nhất một trong hai tiêu đề mô tả/yêu cầu và không kết thúc bằng `...`. Với TopDev, độ dài đúng 6.000 ký tự được xem là dấu hiệu bản cũ bị cắt.
- `fetch_public(page, row)` mở trang tin, đợi tải, thực hiện xử lý riêng cho TopCV và VietnamWorks, kiểm tra trang xác minh rồi gọi hàm tương ứng trong `EXTRACTORS`. Khi có mô tả dùng được, nó ghép kết quả vào dòng gốc.
- `with_retry(fn, *args, delay=...)` bao luồng gọi LinkedIn với tối đa 5 lần thử và khoảng đợi tăng dần sau lỗi. Nếu hết lượt, nó trả lại dòng đầu vào và thông báo lỗi. Khoảng nghỉ giữa hai tin được áp dụng trong `run_linkedin()`.
- `main()` đọc `it.jsonl` và kết quả trước, lập danh sách URL cần tải, áp dụng `--site` và `--limit`, rồi nhóm theo nguồn. LinkedIn chạy trước, sau đó đến các sàn công khai có tin cần xử lý.
  - `flush()` đi theo đúng thứ tự URL đầu vào, dùng bản chi tiết đã có, cập nhật bốn trường của bộ lọc IT và thay `full.jsonl` qua file tạm.
  - `run_linkedin(ctx, subset)` gọi `with_retry()`, lưu định kỳ sau mỗi 20 tin và khi nhóm chạy xong bình thường.
  - `run_public(subset, desc, headless)` chạy vòng thử lại của các sàn công khai, lưu định kỳ sau mỗi 20 tin và thực hiện `flush()` trong `finally`. `open_browser()` mở phiên và tab. `close_browser()` giải phóng tài nguyên và được gọi cả khi cần khởi động lại.
  - Khi kết thúc bình thường, `main()` ghi nhận lỗi của lần chạy hiện tại ở `data/details-errors.jsonl` nếu có lỗi. File này không phải nhật ký tích lũy qua mọi lần chạy.

### Chuẩn hóa lương với clean_salary.py

**Vấn đề.** Lương 12.000 USD/năm và 25 triệu VND/tháng có thể cùng giá trị theo quy ước của bài. Nếu đem hai con số gốc đi tính trung bình, kết quả sẽ trộn tiền tệ và kỳ trả. Điền 0 cho tin “Thỏa thuận” cũng làm trung bình thấp sai.

File quy về **VND/tháng** khi đọc được tiền tệ và kỳ trả, giữ lại dữ liệu gốc trong `salary.jsonl`. Bài dùng tỷ giá cố định **25.000 VND/USD** và chia 12 cho lương năm. Khoảng kiểm tra hợp lý trong code là **1–300 triệu VND/tháng**. [Mã nguồn clean_salary.py](clean_salary.py)

- **Nguồn lương.** Ưu tiên `salary` trên thẻ tin. Nếu trống hoặc đúng thông báo ẩn lương mà code nhận ra, thử `salary_detail` và gợi ý tiền tệ/kỳ trả đi kèm. Lương mô tả chỉ được bổ sung theo điều kiện ở dưới.
- **Giá trị có số.** `closed_range` là đủ hai cận, gồm lương cố định có hai cận bằng nhau. `min_only` và `max_only` giữ một cận đã biết.
- **Giá trị chưa dùng được.** `negotiable` là chuỗi thỏa thuận hoặc mô tả tương tự mà code nhận diện. `hidden` là thông báo cần đăng nhập. `missing` là chuỗi trống. `unknown` là có chuỗi nhưng chưa đủ căn cứ để đọc hoặc đổi đơn vị. `invalid` là giá trị đã quy đổi nhưng nằm ngoài khoảng kiểm tra. Hai cận được để trống trong các trường hợp này.
- **Ngoại lệ TopCV.** Nếu đọc lại với kỳ trả tháng có thể xác định được kỳ trả, tin được đánh dấu `salary_period_assumed`. Ví dụ “15–20 triệu” có thể được tính theo tháng ở TopCV. Nếu tiêu đề hoặc JD ghi lại đúng khoảng đó kèm “/tháng”, cờ giả định được gỡ.

Các hàm xử lý theo thứ tự sau.

- `normalize(text)` hạ chữ, bỏ dấu, chuẩn hóa khoảng trắng và dấu nháy để chuỗi tiếng Việt và tiếng Anh dễ khớp mẫu.
- `parse_salary(raw, currency_hint, period_hint)` đọc **toàn bộ** chuỗi, tách số, tiền tệ, kỳ trả và các từ như “từ” hoặc “tới”. Sau đó hàm quy đổi, kiểm tra thứ tự hai cận và ngưỡng hợp lệ. Dấu phân cách hàng nghìn được xử lý trước khi đổi thành số. Chữ “triệu” hoặc “tr” được coi là triệu VND theo quy ước của bộ phân tích, kể cả một số chuỗi có ký hiệu `$` đi kèm. Gợi ý chỉ bổ sung phần còn thiếu. Ví dụ “12,000 USD/năm” ra hai cận đều là 25 triệu VND/tháng.
- `jd_amount(number)` đổi một số lấy từ JD thành giá trị VND theo quy ước của mẫu. Ví dụ `15.000.000` thành `15000000` và `13,5` được hiểu là 13,5 triệu.
- `monthly_ranges(text)` tìm các khoảng có ghi “/tháng” hoặc “/month”, kiểm tra cận và đánh dấu khoảng có chữ “lương”, “thu nhập”, `salary` hoặc `income` trong 30 ký tự phía trước.
- `clean_row(row)` chọn nguồn, gọi bộ đọc lương và xử lý ngoại lệ TopCV. Nếu lương chính thiếu, bị ẩn, thỏa thuận, chưa đọc được hoặc chỉ có một cận, hàm có thể lấy từ tiêu đề hoặc JD khi chỉ có **một khoảng hợp lệ khác biệt** có nhãn lương và khoảng đó khớp mọi cận đã biết. Ví dụ “Tới 30 triệu/tháng” đi cùng “Mức lương 25–30 triệu/tháng” có thể cho đủ hai cận. Giá trị này được gắn `salary_source="jd"` vì “thu nhập” có thể gồm thưởng.
- `main()` kiểm tra file đầu vào và từ chối dòng đã có các trường lương chuẩn hóa, chạy `clean_row()` cho toàn bộ tin, ghi qua file tạm rồi thay `salary.jsonl`. Nó in số tin theo trạng thái, số tin dùng giả định tháng và tối đa 10 ví dụ `unknown` khác nhau.

### Trích kỹ năng với extract_tech_skill_.py

**Vấn đề.** “ReactJS” và “React.js” nên được đếm chung, còn “React Native” là tên khác. Nếu chỉ tìm từng chuỗi con, chữ “go” trong “go-live” có thể bị đếm thành ngôn ngữ Go.

File gộp tín hiệu từ **tiêu đề + tag + JD**. Từ điển chia thành `tech`, ví dụ Python hoặc React, và `keywords`, ví dụ Agile hoặc AI. Mỗi tên chuẩn chỉ xuất hiện một lần trên một tin, kể cả khi có mặt ở cả ba nguồn. [Mã nguồn extract_tech_skill_.py](extract_tech_skill_.py) · [Từ điển kỹ năng](../data/skill_dictionary.json)

- `skills_in_jd(text, dictionary)` so khớp một lượt trên JD đã chuẩn hóa. Với `C`, `R`, `Go` và `Express`, nó yêu cầu có một kỹ năng khác đứng cạnh và có dấu hoặc từ phân cách phù hợp như dấu phẩy, dấu gạch chéo hoặc “và”. “Java, Go” có thể được nhận, còn đoạn “go-live” đứng riêng thì bị bỏ qua. Với các biến thể dễ nhầm `ai`, `sap`, `solid`, `excel`, văn bản gốc phải có cách viết tương ứng `AI`, `SAP`, `SOLID` hoặc `Excel`.
- `extract_row(row, dictionary)` dùng `match_skills()` cho tiêu đề/tag và `skills_in_jd()` cho JD. Hàm gộp kết quả, loại lặp, chia theo nhóm, rồi sắp xếp mỗi nhóm theo tên. Kết quả giữ `job_url` để bước xuất đối chiếu.
- `main()` nạp cả hai nhóm, xử lý tất cả dòng từ `full.jsonl`, ghi qua file tạm rồi thay `tech_skills.jsonl`. Nó giữ thứ tự tin, in 15 công nghệ và 10 từ khóa xuất hiện nhiều nhất cùng số tin có hoặc thiếu tín hiệu kỹ năng.

### Chuẩn hóa các trường với lam_sach.py

**Vấn đề.** “Thu Duc” và “Ho Chi Minh City” cần về cùng nhóm khi thống kê. “Công ty hoạt động 10 năm” dễ bị nhầm với yêu cầu ứng viên 10 năm. Cụm “hybrid cloud” nói về công nghệ nên không đủ căn cứ để gán hình thức làm việc Hybrid.

Các hàm nhận một chuỗi hoặc một tin và trả lại trường chuẩn hóa để `export_data.py` ghép vào CSV. Những trường suy ra như ngày đăng, kinh nghiệm, cấp bậc và hình thức làm việc có thêm nhãn nguồn. `parse_cities()` cũng được gọi ngay ở bước khử trùng. File này không có lệnh chạy độc lập. [Mã nguồn lam_sach.py](lam_sach.py)

**Thời gian, nơi làm việc và công ty**

- `iso_timestamp(value)` đổi giờ cào từ `17/11/2026 18:29:12` sang `2026-11-17T18:29:12+07:00`. Hàm gắn `+07:00` theo quy ước dữ liệu thu thập, nên đồng hồ máy cào cần dùng giờ Việt Nam.
- `posted_date(row)` ưu tiên ngày từ trường `date_posted`. Nó hiểu mốc mili giây, ngày ISO và giờ ISO có múi giờ. Khi chỉ có chữ “2 tuần trước”, hàm lùi từ `Timestamp` và ghi nguồn `relative`. Ngày tính theo “tháng trước” hoặc “năm trước” là ước lượng.
- `parse_cities(location)` nhận các cách viết thuộc Hà Nội, TP.HCM, Đà Nẵng và Remote, rồi giữ thứ tự chúng xuất hiện. “Hà Nội, TP.HCM” trả về cả hai. Dữ liệu có chữ mà không nhận ra vùng thì trả `["Khác"]`. Chuỗi trống cho danh sách rỗng.
- `work_mode(row)` ưu tiên trường `work_model`, sau đó tìm Remote hoặc Hybrid trong tiêu đề/địa điểm, cuối cùng dùng ngữ cảnh ở JD. Bước đọc JD xét Hybrid trước Remote rồi Onsite, nên “2 ngày WFH mỗi tuần” khác với Remote toàn thời gian. Khi vẫn thiếu tín hiệu, kết quả để trống.
- `clean_company(name, site)` gộp khoảng trắng và gỡ huy hiệu Pro dính đầu tên đối với TopCV khi khớp mẫu. “ProTập đoàn FPT” thành “Tập đoàn FPT”. `company_raw` vẫn lưu chuỗi nguồn.

**Kinh nghiệm và cấp bậc**

- `is_intern(title)` tìm dấu hiệu thực tập, trainee hoặc cộng tác viên trong tiêu đề. Cờ này giúp tách nhóm thực tập khi phân tích lương Fresher.
- `_exp_from_text(text)` tìm số năm nằm gần từ “kinh nghiệm” hoặc `experience`. Hàm bỏ cận dưới trên 15 năm và bỏ ngữ cảnh có dấu hiệu nói về tuổi công ty. “2–4 năm kinh nghiệm” có hai cận, còn “3+ years of experience” có cận dưới 3.
- `parse_experience(row)` ưu tiên trường kinh nghiệm dạng “2 năm”, “dưới 1 năm”, “trên 5 năm” hoặc “không yêu cầu”. Tiếp đó nó thử từ mốc Yêu cầu trong JD rồi thử toàn JD. Cuối cùng nó lấy số tháng của ITviec nếu có và dùng `round(tháng / 12)`, ví dụ 10 tháng thành 1 năm. Giá trị 0 chỉ dùng khi có căn cứ như “không yêu cầu” hoặc cận dưới của “dưới 1 năm”.
- `is_pm_po(title)` nhận Product Manager, Project Manager, Product Owner, Scrum Master và viết tắt `PM`/`PO` trên tiêu đề gốc.
- `seniority(row, exp_min)` ưu tiên cấp bậc ghi trong tiêu đề, rồi nhãn cấp bậc của nguồn, rồi cận dưới kinh nghiệm. Tiêu đề có hai mức thì mức cao hơn được xét trước. Nếu suy từ năm, dưới 1 là Fresher, từ 1 đến dưới 3 là Junior, từ 3 đến dưới 5 là Middle và từ 5 trở lên là Senior. Với PM/PO, “Manager” chỉ mang nghĩa vai trò trong tên chức danh. Mức Lead cần tín hiệu lãnh đạo rõ hơn. CTO/CIO/CISO được xem là Lead khi tiêu đề không có ngữ cảnh trợ lý hoặc báo cáo cho chức danh đó.

**Yêu cầu, phúc lợi và ngoại ngữ**

- `jd_sections(description)` đọc theo từng dòng. Khi thấy tiêu đề như “Yêu cầu ứng viên” hoặc “Quyền lợi”, nó giữ nội dung các dòng sau thuộc mục đó cho đến mốc mục kế tiếp. Đây là lý do cần giữ xuống dòng trong JD trước khi dồn thành một đoạn để xuất.
- `benefits(section)` tìm các nhóm như bảo hiểm, thưởng, nghỉ phép và phụ cấp trong mục phúc lợi. Nó giữ dấu tiếng Việt để phân biệt “thưởng” với “thường”. Không có mục thì trả hai giá trị trống. Có mục nhưng không khớp nhóm nào thì trả `[]` và `0`.
- `languages(description)` đếm các nhóm tiếng Anh, Nhật, Hàn và Trung được nhắc trong JD. Đây là dấu hiệu có nhắc, nên “work with Korean partners” vẫn có thể cho `Korean`. JD trống cho kết quả chưa biết, còn JD có nội dung nhưng không nhắc ngôn ngữ nào cho `[]` và `0`.

### Nhận diện tin đăng chéo sàn với group_jobs.py

**Vấn đề.** Cùng một vị trí có thể được đăng trên ITviec và TopCV bằng tên công ty hơi khác. Nếu đếm mỗi dòng như một việc độc lập, thống kê thị trường có thể đếm dư. Nếu hai bản cùng việc rơi vào cả tập huấn luyện và kiểm tra, điểm mô hình có thể bị thổi phồng.

File giữ mọi dòng để so sánh theo sàn, đồng thời gắn `job_group_id` và chọn đúng một `is_primary` cho mỗi nhóm. Đây là kết quả so khớp theo quy tắc, nên hai việc khác nhau nhưng có tên công ty và tiêu đề giống nhau vẫn có thể bị gom. So khớp chéo sàn hiện không dùng thành phố làm điều kiện. [Mã nguồn group_jobs.py](group_jobs.py)

- `norm_company(name)` chuẩn hóa chữ và bỏ các cụm mang tính pháp lý hoặc địa danh chung như “Công ty”, “TNHH”, “Ltd”, “Việt Nam”. Kết quả chỉ dùng để so khớp.
- `norm_title(title)` bỏ phần trong ngoặc vuông, một số cụm lương và các từ như địa danh, Remote hoặc “gấp”. Chữ trong ngoặc tròn được giữ lại, để “Backend (Java)” còn phân biệt với “Backend (Golang)”.
- `pair_scores(a, b)` chỉ xét cặp khác nguồn. RapidFuzz so tên công ty theo tập từ và so tiêu đề sau khi sắp xếp từ. Cặp được đưa vào danh sách ghép khi **cả hai điểm từ 90 trên 100**.
- `primary_key(row)` xếp bản đại diện theo thứ tự có JD, có `Luong_TB`, nhiều kỹ năng hơn, JD dài hơn, thứ tự ưu tiên nguồn và cuối cùng là `job_uid`. Điều này cho phép một nguồn đứng sau vẫn được chọn nếu có bản ghi đầy đủ hơn.
- `assign_groups(rows)` chỉ so trong các nhóm có cùng từ đầu của tên công ty đã chuẩn hóa, rồi thử gộp cặp có điểm tiêu đề cao hơn trước, dùng điểm công ty để phân xử tiếp. Mỗi lần gộp, hai nhóm phải có tập nguồn rời nhau. Hàm nội bộ `find(i)` tìm nhóm hiện tại của dòng, giúp nối A với B và B với C về cùng nhóm nếu thỏa điều kiện. Cuối cùng hàm chép các dòng và gắn ID dựa trên `job_uid` nhỏ nhất trong nhóm, kể cả nhóm một dòng, rồi chọn bản đại diện. Những biến thể đổi mất từ đầu của tên công ty có thể nằm ngoài phạm vi so sánh.

### Chốt phạm vi và xuất bảng với export_data.py

**Vấn đề.** Ba file trung gian được ghép theo thứ tự. Nếu file lương lệch một dòng so với danh sách tin, một tin có thể nhận lương của tin khác. Nếu chưa duyệt các chức danh mơ hồ, nhóm cần thấy rõ tin nào vẫn chờ quyết định.

File kiểm tra **cả danh sách lẫn thứ tự `job_url`** trong `full.jsonl`, `salary.jsonl` và `tech_skills.jsonl`. Nó chặn URL trùng và dòng thiếu URL hoặc giờ cào. Sau đó file quyết định phạm vi IT, tạo bảng gốc, chuẩn hóa bảng sạch và đánh dấu nhóm nghi trùng. Hai file CSV giữ bản ghi ở cùng thứ tự, cùng `job_uid`. [Mã nguồn export_data.py](export_data.py)

Quyết định cuối được xét từ trên xuống.

1. **`manual`.** Dùng `keep` hoặc `drop` nhóm đã điền cho URL đang xét.
2. **`filter`.** Giữ tin đã được bộ lọc sơ bộ đánh `keep`.
3. **`jd_tech`.** Giữ tin nếu danh sách `tech` có kỹ năng ngoài `GENERAL_TOOLS`. Tên nhãn là `jd_tech`, còn đầu vào thực tế gộp từ JD, tiêu đề và tag.
4. **`ambiguous`.** Giữ nhãn chờ duyệt khi chưa đủ căn cứ. Hai CSV vẫn có thể chứa các dòng này. Tin bị `drop` ở quyết định cuối sẽ bị loại khỏi cả hai CSV.

- `job_uid(row)` tạo mã từ tên sàn và 10 ký tự đầu của mã băm SHA-1 của URL. Hai bảng dùng cùng mã để đối chiếu một tin.
- `final_it_decision(row, tech, manual)` áp dụng bốn mức ưu tiên trên và trả quyết định cùng nguồn. Hàm nhận các tin đã đi tới bước xuất, nên phần duyệt tay này không tự khôi phục tin nằm trong `non_it.jsonl`.
- `read_review(path)` đọc CSV duyệt theo `job_url` và kiểm tra hai cột bắt buộc `job_url`, `quyet_dinh`. Quyết định hợp lệ là trống, `keep` hoặc `drop`. Nếu file chưa có thì trả tập quyết định rỗng.
- `review_rows(rows, skills, review)` lập danh sách tin `ambiguous` thiếu kỹ năng ngoài `GENERAL_TOOLS`, thêm tối đa 400 ký tự đầu JD và giữ lại các quyết định đã ghi. Các tin được xếp theo sàn và tiêu đề để dễ đọc liên tiếp.
- `raw_record(row)` tạo dòng cho `raw_data.csv` với tiêu đề, công ty, lương, địa điểm và JD theo dữ liệu nguồn. Nó thêm mã truy vết, đổi định dạng thời điểm cào và tách đoạn yêu cầu/phúc lợi từ JD. Bảng `raw_data.csv` là bản xuất để đối chiếu của tập đã qua lọc, còn `data/raw/` là dữ liệu danh sách thu ban đầu.
- `clean_record(row, salary, skills, decision)` gọi các hàm ở `lam_sach.py`, lấy thành phố đầu tiên làm `city` và giữ cả danh sách ở `cities`. Nó ghép lương và kỹ năng, tính số kỹ năng, đổi `title_role` của nhóm PM/PO thành `pm_po`, gộp khoảng trắng JD và ghi `has_jd` cùng `jd_chars`. `Luong_TB` chỉ tính khi có đủ hai cận. Phúc lợi được trích từ JD gốc còn xuống dòng.
- `cell(value)` ghi `None` thành ô trống, danh sách và đối tượng thành JSON trong ô CSV, số thực thành số nguyên làm tròn. Ví dụ danh sách kỹ năng được ghi dạng `["Java", "SQL"]`.
- `write_csv(path, columns, records)` ghi đúng thứ tự cột sang file tạm với UTF-8 có BOM để Excel đọc tiếng Việt, sau đó thay file đích. Việc thay file diễn ra theo từng tệp.
- `main()` kiểm tra đầu vào, đọc quyết định tay, lập bản ghi cho các tin được giữ, rồi gọi `assign_groups()` trên bảng sạch. Nó ghi `it_review.csv` trước, sau đó ghi hai CSV nộp và `duplicate_groups.csv`. Tệp nhóm trùng chỉ liệt kê nhóm có từ hai dòng. Cuối cùng chương trình in số tin theo nguồn, trạng thái lương và các chỉ số chất lượng dữ liệu.

## Một tin đi qua toàn bộ quy trình

Giả sử TopCV có hai URL đăng “Backend Developer Java” của cùng công ty ở TP.HCM. Dòng được giữ có lương “20–25 triệu”, kinh nghiệm “2 năm” và tên “ProCông ty A”. Sau khi tải chi tiết, JD nói “Kỹ năng Java, Go và SQL” và “Mức lương 20–25 triệu/tháng”.

1. `duplicate.py` có thể gộp hai URL vì cùng sàn, công ty, tiêu đề và khóa địa điểm.
2. `filter_it.py` giữ tin vì “Backend” nhận diện được vai trò IT.
3. `crawler.fetch_detail` lấy phần mô tả của tin, cắt trước mục “Cách thức ứng tuyển”.
4. `clean_salary.py` thử kỳ trả tháng cho TopCV. Khoảng trong JD xác nhận đúng 20–25 triệu/tháng, nên `salary_period_assumed` được gỡ. Bước xuất tính `Luong_TB` là 22,5 triệu VND/tháng.
5. `extract_tech_skill_.py` có thể nhận Java, Go và SQL từ tiêu đề hoặc JD. Java xuất hiện ở hai nơi vẫn chỉ được ghi một lần.
6. `export_data.py` gọi `lam_sach.py` để gỡ huy hiệu Pro và đọc 2 năm kinh nghiệm. Nếu tiêu đề và nguồn không ghi cấp bậc, 2 năm được phân vào Junior với nguồn `years`. Nếu một bản trên sàn khác đủ giống, `group_jobs.py` gắn chung mã nhóm và chọn một dòng đại diện.

## Chạy lại từ đâu khi có thay đổi

- **Raw mới hoặc sửa cách bỏ trùng.** Chạy từ bước 1 trở đi. Quy tắc thành phố của `parse_cities()` cũng tham gia bước 1.
- **Sửa luật lọc IT hoặc muốn áp dụng từ điển mới ngay khi sàng lọc.** Chạy từ bước 2 trở đi. Bước tải JD tái sử dụng mô tả đã đạt điều kiện và cập nhật kết quả lọc.
- **Tải hoặc bổ sung JD.** Chạy bước 3 cho phạm vi cần tải, rồi chạy lại **cả bước 4 và 5**, sau đó bước 6. Hai file lương và kỹ năng có thể cũ dù danh sách URL giống hệt, nên kiểm tra URL ở bước xuất không phát hiện được trường hợp đó.
- **Chỉ sửa quy tắc lương.** Chạy bước 4 rồi bước 6. **Chỉ sửa trích kỹ năng hoặc từ điển dùng riêng ở bước trích.** Chạy bước 5 rồi bước 6.
- **Chỉ sửa `it_review.csv`, cách chốt phạm vi, cách gom nhóm, hoặc hàm làm sạch chỉ dùng khi xuất.** Chạy lại bước 6.

## Đọc dữ liệu sau khi làm sạch

- Khi đếm **số việc theo các nhóm đã nhận diện**, dùng `is_primary=True`. Khi đối chiếu các sàn, giữ các dòng theo `source`. Nếu chia dữ liệu huấn luyện và kiểm tra, giữ các dòng cùng `job_group_id` ở cùng một phía.
- Khi vẽ lương, tách ô trống khỏi số 0. Có thể tách riêng các dòng `salary_period_assumed=True` hoặc `salary_source="jd"` vì kỳ trả suy đoán và thu nhập trong JD có thể khác cách công bố lương trên thẻ tin.
- Khi dự đoán cấp bậc, dùng `seniority_source` để biết nhãn được tạo từ tiêu đề, nhãn nguồn hay số năm. Nếu đưa lại trường đã dùng để tạo nhãn vào đầu vào, mô hình có thể chỉ học thuộc luật gán nhãn của nhóm.
