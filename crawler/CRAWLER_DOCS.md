# Giải thích thư mục `crawler/` (Dành cho cả nhóm)

Tài liệu này giúp mọi thành viên hiểu nhanh **ý tưởng, công cụ, lý do chọn cách cào và từng bước chạy** của toàn bộ 8 file trong thư mục `crawler/`.

---

## 0. Bức tranh tổng quan (Đọc 30 giây là hiểu)

Thay vì vừa mở danh sách vừa bấm vào từng tin để lấy mô tả công việc (JD), nhóm tách làm **2 giai đoạn**:

```text
[Phase 1: 5 file theo 5 web]        [Pipeline lọc]              [Phase 2: fetch_detail.py]
Cào trang danh sách / API    ───►   Bỏ tin trùng &       ───►   Chỉ mở link của tin IT
(URL, tiêu đề, công ty,             lọc bỏ tin ngoài IT         để lấy JD đầy đủ + lương ẩn
 lương, địa điểm, tag...)           (7.388 → 3.216 tin)         → lưu data/full.jsonl
→ lưu data/raw/*.jsonl
```

**Vì sao tách 2 pha?** Để khỏi tốn thời gian (và đỡ bị web chặn) cho hơn **4.000 tin trùng hoặc không phải IT**.

### Bản đồ 8 file trong `crawler/`

| File | Làm gì / Web nào | Cách cào | Công cụ chính |
|---|---|---|---|
| [base.py](base.py) | Hàm dùng chung | Đọc/ghi JSONL, gắn giờ, vòng lặp cào bán tự động | `json`, `BeautifulSoup` |
| [browser.py](browser.py) | Mở trình duyệt Chrome | Mở Chrome thật, giấu dấu vết bot, lưu phiên đăng nhập | `Playwright` |
| [itviec.py](itviec.py) | **ITviec** (Phase 1) | Tự lật `?page=N`, đợi đúng thẻ tin hiện ra | `Playwright` + `BS4` |
| [topdev.py](topdev.py) | **TopDev** (Phase 1) | Tự lật `?page=N`, tìm link tin rồi leo ngược lên thẻ cha | `Playwright` + `BS4` |
| [vietnamnetworks.py](vietnamnetworks.py) | **VietnamWorks** (Phase 1) | Gọi thẳng API tìm kiếm trả JSON (không mở trình duyệt) | `requests` + `BS4` |
| [topcv.py](topcv.py) | **TopCV** (Phase 1) | Bán tự động: người bấm trang, máy tự đọc & chống trùng | `Playwright` + `BS4` |
| [linkedin.py](linkedin.py) | **LinkedIn** (Phase 1) | Đăng nhập tay 1 lần lưu profile + bán tự động cuộn trang | `Playwright` + `BS4` |
| [fetch_detail.py](fetch_detail.py) | **Cả 5 web** (Phase 2) | Lấy JD đầy đủ & lương ẩn; tự lưu checkpoint mỗi 20 tin | `Playwright` + `BS4` + Voyager API |

---

## 1. Công cụ đã dùng và vì sao

| Công cụ | Dùng để làm gì | Vì sao chọn |
|---|---|---|
| **Playwright** (`channel="chrome"`) | Điều khiển trình duyệt Chrome thật (mở trang, chờ tải, bấm nút, đọc HTML) | Web tuyển dụng hiện đại tải tin bằng JavaScript và có Cloudflare chống bot. Mở Chrome thật giúp chạy đủ JS và ít bị chặn hơn gửi request thô. |
| **BeautifulSoup + `lxml`** | Tìm và bóc chữ từ HTML (`select`, `select_one`) | Playwright chỉ đưa ra cả cục HTML; BeautifulSoup + `lxml` đọc cực nhanh, cú pháp CSS gọn, cả nhóm dễ đọc khi vấn đáp. |
| **`requests.Session`** | Gửi HTTP POST trực tiếp tới API (VietnamWorks) | Khi web đã có API trả thẳng JSON thì không cần mở Chrome — nhẹ máy, nhanh gấp nhiều lần và không sợ vỡ khi web đổi giao diện. |
| **Thư viện chuẩn Python + `tqdm`** | `argparse` (tham số lệnh), `time` + `random` (nghỉ ngẫu nhiên), `json` (lưu JSONL), `tqdm` (thanh tiến độ) | Có sẵn trong Python, không cài thừa thư viện nặng. Nghỉ ngẫu nhiên giúp mô phỏng người thật (và là yêu cầu của đề). |

> **4 thuật ngữ ngắn để đọc code không bị vấp:**
> - **DOM**: Cây cấu trúc HTML đang hiển thị trên trình duyệt (sau khi JavaScript chạy xong).
> - **Selector**: Địa chỉ để chọn đúng thẻ HTML cần lấy (ví dụ `div.job-card` = thẻ `div` có class `job-card`).
> - **JSON-LD (`JobPosting`)**: Khối dữ liệu chuẩn hóa Google/SEO nhúng ẩn trong HTML trang chi tiết — chứa sẵn JD, ngày đăng, thậm chí cả mức lương ẩn.
> - **JSONL**: File text mà **mỗi dòng là 1 tin tuyển dụng dạng JSON** → cào xong trang nào ghi nối ngay trang đó, lỗi giữa chừng không mất dữ liệu cũ.

---

## 2. Hai file nền dùng chung

### [base.py](base.py) — Lưu dữ liệu & vòng lặp cào bán tự động
- **Ý tưởng**: Gom các thao tác lặp lại ở nhiều web vào 1 file để code gọn và thống nhất định dạng.
- **Từng hàm**:
  1. `timestamp(rows)`: Gắn thời điểm cào (`dd/mm/yyyy HH:MM:SS`) vào từng tin để phục vụ kiểm tra audit.
  2. `write_jsonl(path, rows)`: Tự tạo thư mục rồi **ghi nối (`"a"`)** từng dòng JSON UTF-8 (dùng cho ITviec, TopDev).
  3. `read_jsonl(path)`: Đọc file JSONL về danh sách Python (trả về `[]` nếu file chưa có).
  4. `interactive_scrape(page, parse_fn, out_path)`: Dùng cho **TopCV** và **LinkedIn**:
     - Nạp lại file cũ (nếu có) vào bảng tra theo `job_url` để tránh trùng.
     - Chạy vòng lặp cứ **2–3 giây** đọc HTML hiện tại → gọi hàm tách tin → có URL mới thì thêm vào và lưu ra file → dừng khi người dùng nhấn `Ctrl+C`.

### [browser.py](browser.py) — Mở Chrome "giấu dấu vết bot"
- **Ý tưởng**: Dùng `with ... as ctx:` để mở trình duyệt với cấu hình chống phát hiện bot và tự đóng gọn khi xong.
- **Từng hàm**:
  1. `browser(headless=False)`: Mở Chrome thật phiên mới, gắn `USER_AGENT` máy thật, tắt cờ `AutomationControlled` và ẩn `navigator.webdriver`. Dùng cho ITviec, TopDev, TopCV.
  2. `persistent_context(user_data_dir, headless=False)`: Giống trên nhưng **lưu hồ sơ trình duyệt (cookie, đăng nhập) vào thư mục trên máy**. Dùng cho LinkedIn (`data/linkedin-profile`).
  3. `webkit_context(...)`: Hồ sơ WebKit (Safari engine) viết dự phòng, hiện chưa có file nào gọi.

---

## 3. Giải thích từng file cào website (Phase 1)

### 3.1. ITviec — [itviec.py](itviec.py)

- **Ý tưởng**: URL phân trang rất rõ ràng (`?page=2`, `?page=3`...) và thẻ tin có class cố định (`div.job-card`). Do đó cho Playwright **tự lật từng trang** và **chờ đúng thẻ `div.job-card` xuất hiện** rồi bóc dữ liệu.
- **Công cụ**: Playwright (`browser`) + BeautifulSoup (`lxml`).
- **Vì sao chọn cách này? (So sánh với 3 cách khác)**

| Cách cào | So sánh |
|---|---|
| **Playwright tự phân trang + `wait_for_selector` (Chọn)** | Tự động 100%, chạy đủ JS, đọc ngay khi thẻ tin vừa hiện (không thừa thời gian, không đọc sớm). |
| 1. `requests` tải HTML trực tiếp | Nhẹ hơn nhưng ITviec có lớp kiểm tra trình duyệt / Cloudflare → dễ bị chặn 403 hoặc trả trang rỗng. |
| 2. Playwright chờ cứng `sleep(5s)` | Dễ viết nhưng mạng nhanh thì phí thời gian, mạng chậm thì đọc khi thẻ tin chưa tải xong. |
| 3. Bấm tay bán tự động (`interactive_scrape`) | Không cần thiết vì ITviec chỉ có ~32 trang và URL đã có quy luật để tự động hoàn toàn. |

- **Từng bước hoạt động**:
  1. Đọc tham số chạy (`--pages` mặc định 32, `--limit`, `--headless`, `--out`). Nếu file `--out` đã tồn tại → **dừng ngay** để không ghi đè mất dữ liệu cũ.
  2. Mở Chrome qua `browser()`, lặp số trang từ `1` đến `--pages`.
  3. `fetch_page()`: Mở `/it-jobs` (hoặc `?page=N`), đợi `domcontentloaded` rồi đợi thẻ `div.job-card` hiện lên, sau đó lấy HTML.
  4. `parse_card()`: Với mỗi `div.job-card`, cắt bỏ `?query` trên `job_url`, bóc `title`, `company`, `location`, `work_model`, `role_type`, `salary`, `posted_at` (bỏ tiền tố `"Posted "`) và danh sách `skills`.
  5. Gắn `Timestamp`, ghi nối ngay vào `data/raw/itviec.jsonl`, nghỉ ngẫu nhiên **2–5 giây** rồi qua trang tiếp. Dừng khi đủ `--pages`, đủ `--limit` hoặc trang rỗng.

---

### 3.2. TopDev — [topdev.py](topdev.py)

- **Ý tưởng**: TopDev cũng phân trang được bằng `?page=N`, nhưng HTML dùng Tailwind CSS (class kiểu `rounded-[16px]`, không có class ngữ nghĩa rõ như `job-card`). Vì vậy code **bám vào đường dẫn chi tiết `a[href*='/detail-jobs/']` trước**, rồi **leo ngược lên tối đa 7 thẻ cha** để lấy trọn khung thẻ tin.
- **Công cụ**: Playwright (`browser`) + BeautifulSoup (`lxml`).
- **Vì sao chọn cách này? (So sánh với 3 cách khác)**

| Cách cào | So sánh |
|---|---|
| **Playwright tự phân trang + neo vào link tin rồi leo thẻ cha (Chọn)** | Tự động hết ~194 trang; URL `/detail-jobs/` ổn định hơn tên class giao diện; dễ chống trùng link ngay trong trang. |
| 1. `requests` tải HTML trực tiếp | Trang tìm kiếm TopDev dùng JS để dựng danh sách tin → HTML gốc không đủ dữ liệu. |
| 2. Bắt selector cứng của toàn bộ khung card | Giao diện Tailwind không có class tên rõ ràng, web đổi bố cục nhẹ là vỡ selector ngay. |
| 3. Cào bán tự động bấm tay | TopDev có tới ~194 trang (~2.900 tin), ngồi bấm tay quá mất công. |

- **Từng bước hoạt động**:
  1. Đọc tham số (`--pages` mặc định 194, `--limit`, `--headless`, `--out`). Chặn ghi đè nếu file `--out` đã tồn tại.
  2. Mở Chrome, lặp từ trang `1` đến `--pages`.
  3. `fetch_page()`: Mở `https://topdev.vn/jobs/search?page=N`, đợi `domcontentloaded` rồi nghỉ ngẫu nhiên **3–6 giây** (vừa chờ JS render vừa giãn request).
  4. `parse_cards()`: Tìm mọi `a[href*='/detail-jobs/']`, bỏ `?query`, loại link lặp bằng `seen`. Từ mỗi link leo lên tối đa 7 thẻ `.parent` đến khung `rounded-[16px]` để lấy `title`, `company`, `location`, `experience_level`, `salary`, `posted_at`, `skills`.
  5. Gắn `Timestamp`, ghi nối vào `data/raw/topdev.jsonl`. Dừng khi đủ giới hạn hoặc trang trả rỗng. *(Ghi chú: `/jobs/search` có lẫn nhiều tin ngoài IT như ngân hàng → bước `filter_it.py` sẽ lọc bỏ sau).*

---

### 3.3. VietnamWorks — [vietnamnetworks.py](vietnamnetworks.py)

- **Ý tưởng**: Kiểm tra tab Network (F12) thấy VietnamWorks lấy danh sách qua một **API tìm kiếm trả JSON** (`ms.vietnamworks.com/job-search/v1.0/search`) và cho phép lọc sẵn ngành IT (`jobFunction` `parentId: 5`). Do đó **gọi thẳng API bằng `requests`**, không cần mở trình duyệt.
- **Công cụ**: `requests.Session` + BeautifulSoup (`lxml`, chỉ để bỏ thẻ HTML trong mô tả) + ghi file tạm an toàn.
- **Vì sao chọn cách này? (So sánh với 3 cách khác)**

| Cách cào | So sánh |
|---|---|
| **Gọi thẳng Search API bằng `requests` (Chọn)** | Cực nhanh (50 tin/lượt), không mở Chrome, dữ liệu JSON có sẵn tên trường (`jobTitle`, `skills`...), lọc sẵn ngành IT, không sợ vỡ giao diện. |
| 1. Playwright mở Chrome đọc từng thẻ HTML | Chậm và tốn RAM gấp nhiều lần; phải viết CSS selector dễ hỏng trong khi API JSON đã công khai. |
| 2. `requests` tải HTML trang web | VietnamWorks là web tải động (SPA) nên HTML gốc không chứa danh sách tin. |
| 3. Mở luôn trang chi tiết từng tin ngay ở Phase 1 | Chậm vì tải cả tin trùng/ngoài IT. Search API chỉ trả mô tả rút gọn (`...`), nên để Phase 2 tải bù JD cho tin IT là hợp lý hơn. |

- **Từng bước hoạt động**:
  1. Đọc tham số (`--pages` mặc định 16, `--limit`, `--out` mặc định `data/raw/vietnamworks.jsonl`), kiểm tra hợp lệ.
  2. Mở `requests.Session`, duyệt `page_num` từ **0** (API đánh số từ 0). Từ trang thứ 2 nghỉ ngẫu nhiên **1–3 giây**.
  3. `fetch_page()`: Gửi `POST` kèm JSON `BODY` (`hitsPerPage: 50`, lọc ngành IT, danh sách trường `retrieveFields`), timeout 20 giây, kiểm tra mã HTTP và mảng `data`.
  4. `parse_job()`: Chuẩn hóa từng tin — tự ghép `job_url` từ `alias` + `jobId` nếu thiếu; lấy địa điểm đầu tiên, lương (`prettySalary` hoặc `salaryMin-salaryMax`), `skills`, `industries`; gọi `clean_html()` chuyển mô tả & yêu cầu HTML sang chữ thuần.
  5. Gắn `Timestamp`, khử trùng ngay theo `job_url` trong dict `jobs_by_url`.
  6. `write_jobs()`: Ghi ra file tạm cùng thư mục rồi đổi tên sang file đích (atomic write, hỗ trợ `.jsonl` và `.json`). *(Lưu ý: mặc định sẽ ghi đè file cũ nếu không đổi `--out`).*

---

### 3.4. TopCV — [topcv.py](topcv.py)

- **Ý tưởng**: TopCV có Cloudflare chống bot rất chặt nếu script tự nhảy hàng trăm trang liên tục. Nhóm chọn cách **bán tự động**: Chrome mở sẵn danh mục IT, **người dùng tự bấm chuyển trang** (và xác minh nếu bị hỏi), còn code chạy ngầm **tự bóc tin và chống trùng** mỗi 2–3 giây.
- **Công cụ**: Playwright (`browser`) + `interactive_scrape` (`base.py`) + BeautifulSoup (`lxml`).
- **Vì sao chọn cách này? (So sánh với 3 cách khác)**

| Cách cào | So sánh |
|---|---|
| **Bán tự động `interactive_scrape` (Chọn)** | Hạn chế tối đa việc bị Cloudflare chặn; người nhìn thấy trực tiếp trang đã tải xong chưa; máy vẫn tự trích trường và loại trùng URL. |
| 1. Playwright tự lật `?page=1..200` | Dễ bị Cloudflare chặn giữa chừng khiến cả lượt chạy thất bại. *(File có viết sẵn `fetch_page()`, nhưng `main()` hiện dùng vòng tương tác).* |
| 2. `requests` tải HTML trực tiếp | Gần như chắc chắn bị tường chống bot/Cloudflare trả lỗi 403. |
| 3. Copy thủ công từng tin | Hơn 2.400 tin TopCV không thể chép tay, dễ thiếu trường và sai sót. |

- **Từng bước hoạt động**:
  1. Đọc tham số (`--start-page`, `--headless`, `--out` mặc định `data/raw/topcv.jsonl`).
  2. Mở Chrome tới trang danh mục IT của TopCV (thêm `?page=N` nếu `--start-page > 1`), chờ 3 giây.
  3. Chạy `interactive_scrape()`: cứ 2–3 giây lại đọc HTML hiện tại đưa vào `parse_cards()`.
  4. `parse_cards()`: Duyệt các thẻ `div.job-item-search-result`, lấy `job_url` (ưu tiên `h3.title a`, dự phòng `a[href*='/viec-lam/']`), cắt `?query`, bóc `title`, `company`, `location`, `salary`, `experience_level`, `posted_at`.
  5. Gắn `Timestamp`, thêm tin chưa có URL vào `data/raw/topcv.jsonl`. Khi bấm hết trang, người dùng nhấn `Ctrl+C` để dừng.

---

### 3.5. LinkedIn — [linkedin.py](linkedin.py)

- **Ý tưởng**: LinkedIn yêu cầu **đăng nhập** để xem nhiều việc làm và rất nhạy với bot đăng nhập/cuộn tự động. Do đó dùng **hồ sơ Chrome lưu trên đĩa (`data/linkedin-profile`)** để người dùng đăng nhập tay 1 lần rồi giữ cookie cho các lần sau, kết hợp `interactive_scrape` để máy tự thu tin khi người dùng cuộn/lật trang.
- **Công cụ**: Playwright (`persistent_context`) + `interactive_scrape` (`base.py`) + BeautifulSoup (`lxml`).
- **Vì sao chọn cách này? (So sánh với 3 cách khác)**

| Cách cào | So sánh |
|---|---|
| **Profile lưu đăng nhập + `interactive_scrape` (Chọn)** | Đăng nhập tay 1 lần dùng lại cho cả Phase 1 và Phase 2; an toàn cho tài khoản; tránh lỗi tự cuộn/tải dần của LinkedIn. |
| 1. Tự động điền tài khoản/mật khẩu bằng code | LinkedIn rất hay bật CAPTCHA, xác minh email hoặc khóa tạm tài khoản khi thấy login tự động. |
| 2. Cào trang công khai không đăng nhập | Bị giới hạn số tin xem được và nhanh chóng bị ép sang màn hình đăng nhập. |
| 3. Gọi Voyager API cho cả bước tìm kiếm | Payload tìm kiếm phức tạp, hay đổi và dễ bị khóa tài khoản hơn nhiều so với chỉ gọi API lấy chi tiết ở Phase 2. |

- **Từng bước hoạt động**:
  1. Đọc tham số (`--headless`, `--out` mặc định `data/raw/linkedin.jsonl`).
  2. Mở Chrome bằng `persistent_context("data/linkedin-profile")` để giữ phiên đăng nhập.
  3. Đi tới `SEARCH_URL` tìm `software engineer OR developer OR engineer` tại `Vietnam` trong 30 ngày gần nhất (`f_TPR=r2592000`).
  4. Người dùng đăng nhập (nếu cần) rồi cuộn/chuyển trang. Ở nền, `interactive_scrape()` liên tục gọi `parse_jobs()`.
  5. `parse_jobs()`: Quét 3 mẫu thẻ job khác nhau của LinkedIn, rút gọn link về dạng chuẩn `https://www.linkedin.com/jobs/view/<job_id>`, bóc `title`, `company`, `location`, `salary`.
  6. Gắn `Timestamp`, loại trùng theo `job_url`, lưu liên tục vào `data/raw/linkedin.jsonl` đến khi nhấn `Ctrl+C`.

---

## 4. Giai đoạn 2: Tải JD đầy đủ & lương ẩn — [fetch_detail.py](fetch_detail.py)

- **Ý tưởng**: Chỉ chạy **sau khi đã khử trùng và lọc tin IT (`data/it.jsonl`)**. Mỗi website có một hàm trích JD riêng để **JD sạch, không dính menu hay "Việc làm liên quan"**. Hỗ trợ **chạy tiếp (resumable)**: lưu tiến độ vào chính `data/full.jsonl` sau mỗi 20 tin nên mất mạng hay `Ctrl+C` không phải chạy lại từ đầu.
- **Công cụ**: Playwright (profile `data/public-profile` giữ cookie Cloudflare cho 4 sàn công khai; `data/linkedin-profile` cho LinkedIn) + BeautifulSoup (`lxml`) + `tqdm`.

### Cách bóc JD riêng cho từng sàn

| Sàn | Hàm trích | Chiến lược chính |
|---|---|---|
| **ITviec** | `extract_job_posting` | Đọc khối **JSON-LD `JobPosting`** → vừa sạch JD vừa lấy được **lương ẩn** không cần đăng nhập. Nếu tin hết hạn (mất JSON-LD) thì đọc dự phòng `section.job-content`. |
| **VietnamWorks** | `extract_vietnamworks` | Tự bấm nút `"Xem đầy đủ"` (nếu có), lấy theo 3 mục: *Mô tả công việc*, *Yêu cầu công việc*, *Các phúc lợi dành cho bạn* (bỏ khung *"Mức độ phù hợp"*). Dự phòng JSON-LD. |
| **TopDev** | `extract_topdev` | Chọn khung thẻ JD dài nhất (≥ 400 ký tự, có từ khóa JD, bỏ khung *"More jobs for you"*). Lấy thêm **lương ẩn** từ JSON-LD. |
| **TopCV** | `extract_topcv` + `trim_topcv_text` | Kiểm tra chuyển hướng để phát hiện tin bị gỡ; xóa `script/style` rồi cắt text từ mốc *"Mô tả công việc"* / *"Job Description"* đến trước *"Cách thức ứng tuyển"* / *"Việc làm liên quan"*. Dưới 300 ký tự thì báo lỗi thử lại. |
| **LinkedIn** | `fetch_linkedin` | Dùng cookie đã đăng nhập (`JSESSIONID` làm `csrf-token`) gọi thẳng **Voyager JSON API** (`/voyager/api/jobs/jobPostings/{id}`). Nhanh (0,3s/tin) và tránh lỗi trang HTML tự chuyển hướng sang trang công ty. |

### Vì sao chọn cách lấy JD này? (So sánh với 3 cách khác)

| Cách lấy JD | So sánh |
|---|---|
| **Tách Phase 2 + bộ trích riêng từng sàn + checkpoint 20 tin (Chọn)** | Giảm >50% lượt tải trang, JD sạch (tránh trích sai kỹ năng từ tin gợi ý), lấy được lương ẩn ITviec/TopDev, dừng giữa chừng chạy tiếp được. |
| 1. Lấy luôn JD lúc cào Phase 1 | Phải mở hàng nghìn trang tin trùng và ngoài IT → chậm gấp đôi, tăng nguy cơ bị khóa IP. |
| 2. Dùng chung 1 hàm lấy toàn bộ chữ `<body>` cho cả 5 web | Ít code nhưng dính menu, footer và "Việc làm liên quan" → làm sai toàn bộ bước trích kỹ năng phía sau. |
| 3. Chỉ dùng JSON-LD cho cả 5 web | Đơn giản nhưng VietnamWorks thiếu mục Yêu cầu trong JSON-LD, còn LinkedIn/TopCV không đáp ứng đủ. |

### Từng bước hoạt động của `fetch_detail.py`

1. **Khôi phục tiến độ**: Đọc `data/it.jsonl` và các tin đã có trong `data/full.jsonl`. Hàm `description_complete()` tự nhận ra tin nào cần tải (trống JD, VietnamWorks bị cụt `...`/thiếu mục, hoặc TopDev bị cắt đúng 6.000 ký tự cũ).
2. **Chia nhóm theo sàn**: Áp dụng `--site`, `--limit` (nếu có), gom các tin cần tải theo từng sàn bằng `site_of()`.
3. **Chạy LinkedIn trước**: Mở `data/linkedin-profile`, gọi Voyager API từng tin (thử lại tối đa 5 lần nếu lỗi, nghỉ 0,3 giây/tin).
4. **Chạy 4 sàn công khai** (`itviec` → `topdev` → `topcv` → `vietnamworks`): Mở Chrome dùng `data/public-profile`, nghỉ ngẫu nhiên **1,5–4 giây/tin**. Nếu `is_cloudflare()` phát hiện trang xác minh:
   - Chạy có cửa sổ: chờ tối đa 180 giây để người dùng bấm xác minh.
   - Vẫn bị chặn: báo `CloudflareDetected` → đóng và mở lại trình duyệt, thử lại tối đa 5 lần.
5. **Lưu checkpoint an toàn**: Sau mỗi **20 tin** (và trong `finally` kể cả khi nhấn `Ctrl+C`), `flush()` ghi ra file `.tmp` rồi đổi tên thành `data/full.jsonl` (đồng bộ luôn 4 cột lọc IT mới nhất). Các tin hỏng sau 5 lần thử được ghi vào `data/details-errors.jsonl`.

---

## 5. Nhắc nhanh cho buổi demo & vấn đáp

- **Chạy thử an toàn** (ghi vào `data/demo/` để không chạm dữ liệu thật):
  ```powershell
  python -m crawler.itviec --pages 1 --limit 5 --headless --out data/demo/itviec.jsonl
  python -m crawler.topdev --pages 1 --limit 5 --headless --out data/demo/topdev.jsonl
  python -m crawler.vietnamnetworks --pages 1 --limit 5 --out data/demo/vietnamworks.jsonl
  python -m crawler.topcv --start-page 1 --out data/demo/topcv.jsonl
  python -m crawler.linkedin --out data/demo/linkedin.jsonl
  ```
- **3 câu hỏi giảng viên dễ hỏi**:
  1. *Playwright và BeautifulSoup khác nhau ở đâu?* → **Playwright** điều khiển Chrome mở trang và chờ JS tải xong HTML; **BeautifulSoup** nhận chuỗi HTML đó rồi tìm đúng thẻ chứa tiêu đề, công ty, lương...
  2. *Vì sao VietnamWorks không dùng Playwright?* → Vì VietnamWorks có API tìm kiếm trả thẳng JSON 50 tin/lần, dùng `requests` nhanh và ổn định hơn mở Chrome.
  3. *Làm sao tránh bị web chặn khi cào?* → Tách 2 pha để giảm số request, nghỉ ngẫu nhiên (`random.uniform`), mở Chrome thật giấu cờ `webdriver`, lưu profile cookie (`persistent_context` / `public-profile`), và dùng chế độ bán tự động với web chặn gắt (TopCV, LinkedIn).

> Bước làm sạch dữ liệu sau khi cào xem tiếp tại [pipline/PIPELINE_DOCS.md](../pipline/PIPELINE_DOCS.md).
