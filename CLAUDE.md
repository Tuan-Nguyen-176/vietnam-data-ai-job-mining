# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

University group assignment (ITEC3417, "Nhóm 4"): a KDD pipeline over Vietnamese IT job postings (all IT roles; the plan originally scoped web/mobile developers only). Stages: self-written crawler → raw data → cleaning → EDA → clustering → association rules → classification.

`BaiTapLon.pdf` is the assignment brief. The group's plan `KE_HOACH_BAI_TAP_LON_NHOM_4.md` (scope, target raw/clean schemas in section 2, per-member tasks in section 3, advanced checks in section 5), the workflow diagram and the `test_*.py` files are **not in this git repo** (only stale `__pycache__/test_*.pyc` remain); ask for them before designing new stages. `README.md` is a placeholder. `output/pdf/danh-gia-du-lieu-tuyen-dung.pdf` is a data-quality report generated before the last export (numbers may lag `clean_data.csv`).

## Hard requirements from the brief (graded, checked at a live demo)

- **Raw data**: ≥ 800 postings (aim 1,500+) from ≥ 1 platform (2 preferred), with **original, un-normalized text**: title, company, location, raw salary string, required experience, full JD, benefits/requirements. Deliverable names: `raw_data.csv`, `clean_data.csv`.
- **Data audit**: every raw row must have `URL_Goc` (direct link to the posting) and `Timestamp` (collection time). The lecturer opens random links to compare with the live posting.
- **Crawler**: self-written (no paid scraping services), in `scraper.py` or `crawler.ipynb` with `requirements.txt` and run instructions; must handle pagination and dynamic loading and use **random** delay/sleep. It will be run live on a few pages during the defense.
- **Cleaning (2.1)**: regex salary parsing into `Luong_Min` / `Luong_Max`, one currency (VND or USD), an explicit strategy for "Thỏa thuận"; normalize city (Hà Nội, TP.HCM, Đà Nẵng, Remote) and years of experience; strip HTML, remove VI/EN stop words, build a skill dictionary → one-hot matrix or skill list.
- **EDA (2.2)**: salary by level (Fresher/Junior/Middle/Senior/Lead), top 15 skills, region comparison.
- **Clustering (2.3)**: K-Means or hierarchical on skills/requirements; choose K with Elbow + Silhouette; name each cluster.
- **Association rules (2.4)**: Apriori or FP-Growth on skill baskets; filter by support, confidence, **lift > 1.2**, conviction; flag misleading rules.
- **Classification (2.5)**: salary band (e.g. < 15M, 15–30M, > 30M) or level (Junior/Middle/Senior); **Decision Tree with `ccp_alpha` pruning** plus ≥ 1 comparator (KNN / Random Forest / Logistic Regression); confusion matrix, precision, recall, macro F1, error analysis; avoid data leakage.
- **Notebook**: `NhomXX_MiningPipeline.ipynb` must run top to bottom without errors. Every member must be able to explain any code (random oral questions), so prefer plain, explainable code over copied templates.

## Running things

No build system or linter; git repo on `main`. Python 3.14 with `playwright` (Chrome channel: `playwright install chrome`), `beautifulsoup4`, `lxml`, `requests`, `tqdm`, `rapidfuzz` (cross-source grouping in `export_data`); `pandas` for checks. Scripts import `crawler.*` / `pipline.*` as packages, so **run from the repo root as modules** (`.vscode/settings.json` sets `PYTHONPATH` to the repo root for the VS Code terminal):

```
python -m crawler.itviec --pages 3 --limit 50 --headless --out data/raw/demo_itviec.jsonl  # refuses if --out exists
python -m crawler.topdev --pages 2 --headless --out data/raw/demo_topdev.jsonl
python -m crawler.vietnamnetworks --pages 1 --out data/raw/demo_vnw.jsonl   # default --out OVERWRITES data/raw/vietnamworks.jsonl (K1)
python -m crawler.topcv                                       # manual: click pages in the browser, Ctrl+C to stop
python -m pipline.duplicate                                   # data/raw/*.jsonl -> data/dedup.jsonl
python -m pipline.filter_it                                   # data/dedup.jsonl -> data/it.jsonl + data/non_it.jsonl
python -m crawler.fetch_detail --in data/it.jsonl --site topcv --headless   # -> data/full.jsonl (resumable); moved from pipline/ on 2026-11-20
python -m pipline.extract_tech_skill_                         # data/full.jsonl -> data/tech_skills.jsonl
python -m pipline.clean_salary                                # data/full.jsonl -> data/salary.jsonl
python -m pipline.export_data                                 # -> raw_data.csv + clean_data.csv + data/it_review.csv + data/duplicate_groups.csv
# fill quyet_dinh (keep/drop) in data/it_review.csv, then rerun export_data (decisions are kept across reruns)
# tests (33, root-level test_*.py) are missing from this repo; once copied back to the root:
python -m unittest -v test_filter_it test_extract_tech_skill test_clean_salary test_export_data test_fetch_detail test_group_jobs
python -m unittest -v test_export_data.ExportDataTest.test_experience                            # one test
```

After any change to `data/full.jsonl`, rerun `extract_tech_skill_` **and** `clean_salary` before `export_data`: it joins the three files by `job_url` order and refuses if they differ.

On this Windows machine stdout is cp1252; set `PYTHONIOENCODING=utf-8` (or `python -X utf8`) when piping output that contains Vietnamese. `pipline/` is the real, misspelled directory name; it has no `__init__.py` and relies on namespace packages.

## Architecture

**Phase 1 – listing crawl (`crawler/`)**: one module per source, each producing rows with the common keys `site, job_url, title, company, location, salary, posted_at, skills, Timestamp, ...`.
- `itviec.py`, `topdev.py`: Playwright (real Chrome) page-by-page, parse job cards with BeautifulSoup, append each page via `write_jsonl`.
- `vietnamnetworks.py`: no browser; POSTs to the `ms.vietnamworks.com` search API, gets **truncated** description HTML plus `experience_level`, `industries`. Output suffix decides format (`.jsonl` line-delimited, otherwise JSON array); written atomically via a temp file.
- `topcv.py`, `linkedin.py`: use `base.interactive_scrape`, which re-reads the DOM in a loop while a human paginates, dedups by `job_url`, and rewrites the whole file each loop until Ctrl+C. `--pages/--limit/--scrolls` are not wired into these loops.
- `base.py`: `read_jsonl`, `write_jsonl` (**append mode**: delete/replace the output before each run), `timestamp(rows)` stamps `%d/%m/%Y %H:%M:%S` local time. `browser.py`: Playwright context managers (anti-automation flags, UA string).

**Phase 1.5 – `pipline/duplicate.py`**: reads only `data/raw/*.jsonl`, drops duplicate `job_url`, then collapses same `site + company + title + city` (`city_key` via `lam_sach.parse_cities`; intra-site only; keeps the richer record). Same title in different cities stays separate (K15, 2026-11-20). No cross-site dedup here (that is `group_jobs`).

**Phase 1.6 – `pipline/filter_it.py`** (no LLM): signals `title_role` (`role_of`: `non_it_function` → `machine_programming` → an `IT_ROLES` role → `generic` → `unknown`) and `skill_hits` (tags matching group `tech` of `data/skill_dictionary.json`, ignoring `GENERAL_TOOLS` = Excel/Photoshop/AutoCAD/PLC/Figma/Visio/BPMN/CRM/ERP/Jira/Power BI/Tableau/ISO 27001, which also appear in non-IT jobs). `drop` only when surely non-IT; `keep` = IT role title, or generic title + ≥ 1 tech tag; `ambiguous` (kept) = generic title without tags, unclear title with tags, any unclear ITviec title. Output `data/it.jsonl` (keep + ambiguous) and `data/non_it.jsonl` (with reason).

**Phase 2 – `crawler/fetch_detail.py`** (moved here from `pipline/` on 2026-11-20; `pipline/PIPELINE_DOCS.md` and the error text in `extract_tech_skill_.py:75` still say `pipline.fetch_detail`): for rows whose description is not "complete" (`description_complete`), opens the detail page and runs a per-site extractor (`EXTRACTORS`: JSON-LD `JobPosting` for ITviec, section scrape for VietnamWorks, card heuristics for TopDev, Voyager API for LinkedIn with the logged-in profile `data/linkedin-profile`). TopCV: `trim_topcv_text` keeps body text from the line "Mô tả công việc"/"Job Description" up to the first `TOPCV_ENDS` marker ("Cách thức ứng tuyển", "Việc làm liên quan"…); < 300 chars → error, retried later. ITviec/TopDev also get `salary_detail*` from JSON-LD `baseSalary` (no login needed). Resumable: `data/full.jsonl` is output and checkpoint (flushed every 20 rows via temp file + `replace`, and in `finally` on Ctrl+C); failures go to `data/details-errors.jsonl`. Cloudflare interstitials trigger a browser restart.

**Phase 3 – derived files, all read `data/full.jsonl` only**:
- `extract_tech_skill_.py` → `data/tech_skills.jsonl` `{job_url, title, tech[], keywords[]}`. Dictionary `data/skill_dictionary.json`: canonical name + VI/EN aliases + `group` (`tech` = language/framework/DB/tool; `keywords` = cloud/architecture/method/domain). `filter_it.load_dictionary(groups=...)` is shared: the filter loads only `tech`, extraction loads both.
- `clean_salary.py` → `data/salary.jsonl` (all input fields + `Luong_Min/Max` VND/month, `salary_status`, `salary_currency_orig/period_orig`, `salary_source`, `salary_period_assumed`). Fixed rate `USD_TO_VND = 25_000`, yearly ÷ 12, negotiable/hidden/missing/invalid → null, never 0; values outside `MIN_MONTHLY_VND`–`MAX_MONTHLY_VND` (1M–300M) → `invalid`. `parse_salary()` is site-agnostic and never guesses a period; the only exception lives in `clean_row()`: TopCV strings without a period are re-parsed with `period_hint="month"` and flagged `salary_period_assumed=True` (rationale in the module docstring). Status list is in the module docstring.
- `lam_sach.py`: pure functions, no I/O, no `main()` (callable from the notebook for before/after demos): `parse_cities`, `parse_experience`, `seniority`, `is_intern`, `is_pm_po`, `posted_date`, `work_mode`, `jd_sections`, `benefits`, `languages`, `clean_company`, `iso_timestamp`. Each returns a value plus its source (`field`/`title`/`jd`/`years`/`relative`…) so classification can drop label-generating features. Matching runs on `filter_it.normalize()` text (no diacritics) except `BENEFIT_RE` (with diacritics: "thưởng" ≠ "thường").
- `group_jobs.assign_groups(clean_rows)`: marks the same job posted on several sites (no row removed): block by first company word, `rapidfuzz` `token_set_ratio(company) ≥ 90` and `token_sort_ratio(title) ≥ 90`, union-find by best score, never two rows of one source in a group → `job_group_id` (stable sha1) + one `is_primary` per group (`SOURCE_RANK` itviec > vietnamworks > topcv > linkedin > topdev).
- `export_data.py` only joins the three JSONL files, applies the IT decision, calls `lam_sach` + `group_jobs`, and writes `raw_data.csv` (21 columns: original text + `requirements_raw`/`benefits_raw` cut by `jd_sections`) and `clean_data.csv` (41 columns, see below), plus `data/duplicate_groups.csv` (groups ≥ 2 rows, for manual checks). UTF-8-BOM, atomic temp-file write, lists as JSON arrays in cells, `Timestamp` as ISO `+07:00`. Column conventions are in its module docstring.
  **Chốt tập tin IT** (`final_it_decision`): manual (`data/it_review.csv`, overrides everything) → filter `keep` → `jd_tech` (ambiguous with ≥ 1 JD tech outside `GENERAL_TOOLS`) → still `ambiguous`, listed in `it_review.csv`. `drop` rows are left out of both CSVs; `it_decision_source` records why. Rows already decided are never removed from `it_review.csv`. `fetch_detail` refreshes `it_decision/it_reason/title_role/skill_hits` from `it.jsonl` on every run, so rerun it (it may fetch 0 rows) after `filter_it`.

**Matching traps already handled (keep them when editing the dictionary or regexes)**: `IT/AI/ML/BI/SAP/QA/QC/BA/PM` matched case-sensitively on the raw title ("Ba Vì", "thiết bị", "sắp xếp"); whole-word matching (`test` ≠ "Contest"); `_` → space ("Devops_SRE"); no `server` keyword (restaurant "Server"); `English/AI/Cloud/Agile` are `keywords`, not counted in `skill_hits`; aliases longest-first (`React Native` ≠ `React`); `C/R/Go/Express` only inside a real list (`C/C++`, `Java, Go`; not `R&D`, `go-live`, `SAP R/3`); `AI/SAP/SOLID` only when uppercase in the source; `Unity Catalog` → Databricks.

`pipline/PIPELINE_DOCS.md` (466 lines, Vietnamese) explains every pipeline step/function for the whole group; read it before re-explaining the pipeline. The old `*.py.bak*` backups were deleted (2026-11-20); rely on git history.

**Repo-health trap (2026-11-20)**: commit `02ced55` ("d") committed an unresolved merge conflict (`<<<<<<< HEAD … ======= … >>>>>>> 78def91`) into `CLAUDE.md`, `clean_data.csv` and `raw_data.csv`; the two halves were identical except CRLF vs LF (`core.autocrlf=true`, no `.gitattributes`). `CLAUDE.md` is fixed; the CSVs at HEAD are still **unreadable** by pandas (`Expected 21 fields…`). Good copy: `git checkout 7e5d97d -- clean_data.csv raw_data.csv`, or regenerate with `python -m pipline.export_data`. Before any analysis run `grep -c '^<<<<<<<' clean_data.csv raw_data.csv` (expect 0).

## Data layout

`data/raw/` holds `itviec.jsonl`, `topdev.jsonl`, `topcv.jsonl`, `vietnamworks.jsonl`, `linkedin.jsonl`. Everything else under `data/` is derived; `data/it_review.csv` is the only hand-edited file (column `quyet_dinh`, save as "CSV UTF-8" if edited in Excel). The LinkedIn browser profile (`data/linkedin-profile`, cookies) is not in this repo, so `fetch_detail --site linkedin` cannot run here; **never commit it**. Never use file mtime as a collection time. `__pycache__/` is committed by mistake (remove before submitting, G5).

## Conventions

Comments and docstrings are mixed Vietnamese/English; keep new user-facing text consistent with the surrounding file. Data files are UTF-8 with Vietnamese diacritics, so always open with `encoding="utf-8"` (`clean_data.csv`/`raw_data.csv` are `utf-8-sig`; `pd.read_csv` handles both). Code must stay explainable at the oral defense: plain loops/regex over clever one-liners.

---

## Tiến độ (cập nhật 2026-11-20; số liệu theo `clean_data.csv` xuất 2026-11-19 17:21, bản sạch ở commit `7e5d97d`)

**Thay đổi từ 2026-11-19 → 11-20 (commit `02ced55`…`720af7a`):** `fetch_detail.py` chuyển sang `crawler/`; xóa 10 file `.bak*`, `crawler/api_key_vietnamnetwork.py`, `crawler/dump_linkedin.py` và thư mục `.git copy/`; thêm `pipline/PIPELINE_DOCS.md`; **lỗi**: conflict marker nằm trong 2 CSV (xem "Repo-health trap"). Chưa có thay đổi nào ở logic crawler/làm sạch; số liệu dưới đây đã đo lại trên bản CSV sạch và vẫn đúng.

**Thứ tự nên làm và vì sao (tóm tắt):** (0) sửa 2 CSV hỏng → mọi bước sau đọc chúng; (B) khóa clean v1 → EDA/cụm/luật/phân lớp chạy song song cùng một mẫu số, đổi dữ liệu sau đó là làm lại cả bốn; (A5–A7) stop word + one-hot → đầu vào chung của cụm, luật, phân lớp và là yêu cầu 2.1 của đề; (K1–K3, K6, K8, K12) crawler → bị chấm ở buổi demo live, lỗi ở đây là mất điểm ngay trước giảng viên; (C → D → E → F) theo thứ tự đề, vì tên cụm (D) giải thích luật (E), nhãn cấp bậc (A4) quyết định phân lớp (F); (G) đóng gói cuối cùng vì phụ thuộc vào số liệu chốt.

### Cào dữ liệu – tóm tắt việc đã làm

- **5 nguồn, crawler tự viết**: ITviec, TopDev (Playwright, tự phân trang), VietnamWorks (gọi API search, tự phân trang), TopCV và LinkedIn (người bấm trang, script đọc DOM liên tục). Nội dung tải động xử lý bằng Playwright chờ render; **delay ngẫu nhiên** (`random.uniform`) ở mọi crawler và `fetch_detail.py`.
- **Audit**: 100% dòng có `job_url` → `URL_Goc` và `Timestamp` (một định dạng duy nhất `%d/%m/%Y %H:%M:%S`, export đổi sang ISO; 17/11 17:37 → 22:07 +07:00). `itviec.py`/`topdev.py` từ chối ghi đè file `--out` có sẵn (an toàn khi demo). Crawler **chưa sửa gì kể từ 2026-11-18** (K1–K16 vẫn mở, trừ K4/K5 ở `fetch_detail`).
- **JD chi tiết + lương ẩn** (trên tập đã chốt): ITviec 574/598, VietnamWorks 561/561, TopDev 68/68, LinkedIn 682/682, TopCV 1.287/1.295 (8 lỗi trong `details-errors.jsonl`, chủ yếu tin hết hạn/mẫu trang lạ). Lương ITviec/TopDev lấy từ JSON-LD trang chi tiết.
- **Phễu số liệu** (dùng cho báo cáo "dòng nhận → tin dùng được"):

| Nấc | Số tin |
|---|---|
| Raw `data/raw/*.jsonl` | 7.388 (TopDev 2.910, TopCV 2.426, LinkedIn 747, VietnamWorks 701, ITviec 604) |
| `dedup.jsonl` | 7.291 (tạo 17/11 khi LinkedIn mới có 699 tin; chạy lại phễu để lấy thêm 48 tin) |
| `filter_it` giữ (`it.jsonl` = `full.jsonl`) | 3.216 = 2.653 keep + 563 ambiguous (TopCV 1.298, LinkedIn 683, ITviec 598, VietnamWorks 562, TopDev 75); 4.075 tin `non_it.jsonl` |
| Sau chốt IT = `raw_data.csv` = `clean_data.csv` | **3.204** = 2.653 `filter` + 285 `jd_tech` + 266 còn `ambiguous`; bỏ 12 tin `drop` tay (cơ khí, cơ điện/HVAC, QS xây dựng, QC nhà máy thép, dầu khí) |
| Việc làm riêng (`is_primary`) | 3.135; 67 nhóm ghép chéo nguồn (136 dòng, `data/duplicate_groups.csv`) |
| Có JD | 3.172 (thiếu: ITviec 24, TopCV 8) |
| Có ≥ 1 / ≥ 2 tech skill | 2.774 / 2.397 |
| Có lương khoảng đóng (`Luong_TB`) | **767** (TopCV 518, ITviec 129, VietnamWorks 105, TopDev 10, LinkedIn 5); 529 là TopCV giả định lương tháng → **357** tin có kỳ trả có căn cứ |

### Pipeline code

- [x] `duplicate.py`, `filter_it.py`, `fetch_detail.py`, `extract_tech_skill_.py`, `clean_salary.py`, `export_data.py`.
- [x] 2026-11-19: tách chuẩn hóa trường ra **`lam_sach.py`** (`export_data.py` 537 → 255 dòng, bản cũ `export_data.py.bak_truoc_tach_21`); thêm **`group_jobs.py`** (B2, ghép chéo nguồn bằng `rapidfuzz`).
- [ ] **File test không có trong repo** (33 test của `test_*.py` chỉ còn `.pyc` trong `__pycache__/`): chép lại từ thư mục làm việc cũ và chạy lại trước khi sửa code tiếp; `lam_sach.py` sau khi tách chưa được kiểm bằng test trong repo này.
- [x] `raw_data.csv` (3.204 × 21), `clean_data.csv` (3.204 × 41) đã xuất – **chưa khóa** (B5).
- [~] `EDA.ipynb`: đã đọc bằng đường dẫn tương đối `pd.read_csv("clean_data.csv")`; ô 2 còn biến `file_path` tuyệt đối không dùng (xóa đi); vẫn chỉ có `head/describe/info/isna`, chưa có biểu đồ C1–C6. Ô đọc file đang `.drop(columns=["work_mode"])`.
- [x] `output/pdf/danh-gia-du-lieu-tuyen-dung.pdf` – báo cáo đánh giá dữ liệu (tạo 09:42, trước lần export cuối).

### Đánh giá `raw_data.csv` / `clean_data.csv` (kiểm lại 2026-11-19)

**Đạt (đủ để làm EDA, cụm, luật):** 3.204 dòng ≥ 800; `job_uid` khớp 1–1 giữa raw và clean, 0 trùng URL; 100% có `URL_Goc` + `Timestamp`; `title_raw` giữ nguyên văn bản gốc; 0 thẻ HTML/`&nbsp;` trong JD; JD TopCV sạch (bắt đầu ở "Mô tả công việc"/"Job Description", 0 dòng dính footer); raw có `requirements_raw` 2.601 / `benefits_raw` 2.545 tin; 0 tên công ty clean còn tiền tố "Pro".

**Lương theo cấp bậc (median, n có `Luong_TB`)**:

| Tập | Fresher | Junior | Middle | Senior | Lead |
|---|---|---|---|---|---|
| Tất cả 767 tin | 11,5M (114) | 18M (284) | 30M (138) | 37,5M (83) | 30M (111) |
| Chỉ `salary_period_assumed == False` (357) | 10M (29) | 21M (119) | 31,2M (73) | 40M (59) | 41,2M (40) |
| `is_primary` và không `is_intern` | 14M (74) | 18M (281) | 30M (137) | 37,5M (82) | 30M (110) |

Bản đủ dữ liệu có Lead < Senior vì 86/111 tin Lead có lương là TopCV (median 27,5M, so với ITviec 66,3M n=17) → khi báo cáo, trình bày bản `salary_period_assumed == False` cạnh bản đầy đủ.

**Chưa sạch – cần xử lý hoặc ghi vào báo cáo:**

1. **Lương dựa vào giả định**: 529/767 tin có `Luong_TB` là TopCV `salary_period_assumed=True` (`clean_salary` đã bỏ cờ cho tin có tiêu đề/JD ghi lại "/tháng", và lấy 17 khoảng từ JD với `salary_source = "jd"`, có thể là tổng thu nhập). Mọi biểu đồ lương phải ghi chú.
2. **Ngoại lai lương (C5)**: 1 tin > 150M (TopCV CTO "5,000 - 10,000 USD" = 187,5M), 11 tin < 3M đều là thực tập/cộng tác viên. Đã có cột `is_intern` (109 tin) để tách khi vẽ lương Fresher.
3. **Phạm vi IT**: còn **266 tin chờ đọc tay** trong `data/it_review.csv` (TopCV 137, VNW 67, ITviec 36, LinkedIn 22, TopDev 4; phần lớn PO/PM/BA, `title_role = "pm_po"` có 187 tin). 12 tin đã `drop`. Tin phần cứng/bán dẫn (SoC, RTL) được `jd_tech` giữ nhờ Python/C: nhóm quyết phạm vi, muốn loại thì thêm dòng `drop`. Cụm/luật nên dùng `n_tech ≥ 2`; EDA nên chạy thêm bản `it_decision == "keep"`.
4. ~~Tên công ty TopCV dính "Pro"~~ – xong ở clean (`lam_sach.clean_company`); `company_raw` giữ nguyên. Gốc ở crawler (K10) chưa sửa: `posted_at_raw` TopCV vẫn dạng "Đăng2 tuần trước".
5. **Trùng lặp chéo nguồn** – xong phần code (B2, `group_jobs`): 67 nhóm, 136 dòng; **chưa kiểm tay** `data/duplicate_groups.csv`. Tin cùng công ty có JD giống hệt nhưng khác title (Axon, Huawei, HCLTech…) không bị ghép – nếu cần, gom thêm bằng hash JD trước khi chia train/test.
6. **JD LinkedIn có đuôi boilerplate** (EEO, "Recruitment fraud…") – không ảnh hưởng `tech`, nhưng phải bỏ khi làm `jd_clean`/TF-IDF (A5).
7. **Requirements/benefits**: xong ở raw (`jd_sections`) và clean (`benefits`/`n_benefits` 2.545 tin, `languages`/`n_languages` 3.172 tin). LinkedIn chỉ tách được ít (JD viết tự do). Còn thiếu: nhiều địa điểm VNW, `salaryMin/Max` VNW (K7).
8. **Cột thưa**: `work_mode` 75% trống (809 có: Onsite 502, Hybrid 255, Remote 52; Onsite gần như chỉ ITviec), `exp_min_years` trống 495, `city` trống 15, `industries_raw`/`experience_months_raw` rất thưa – không dùng làm đặc trưng chính.
9. **Seniority vẫn dựa nhiều vào số năm**: `years` 1.702, `title` 1.238, `level_field` 24, trống 240 → giữ chặn leakage ở F2. ITviec: `exp_source` = `jd` 441 / `field` 88 sau khi sửa A3.
10. **Lương theo vùng**: Đà Nẵng 40 tin, chỉ 8 có `Luong_TB` → báo "chưa đủ mẫu". Median HN 23M (451), HCM 22M (238).

**Kết luận**: dữ liệu đủ sạch để làm EDA/cụm/luật. Trước khi **khóa clean v1** (B5): chép lại file test và chạy qua, kiểm tay `duplicate_groups.csv`, đọc xong 266 tin trong `it_review.csv`, kiểm ngoại lai (C5).

### Lỗi / rủi ro đã biết (ngoài crawler)

1. Chưa có: `scraper.py` (hoặc `crawler.ipynb`), `requirements.txt` (nhớ có `rapidfuzz`), README lệnh chạy (README hiện chỉ 2 dòng), notebook `NhomXX_MiningPipeline.ipynb`. File kế hoạch không nằm trong repo; bản ở thư mục cũ vẫn ghi phạm vi web/mobile – cần sửa thành "mọi vị trí IT".
2. `data/raw/linkedin.jsonl` được `interactive_scrape` ghi lại toàn bộ mỗi 2–3 giây khi crawler đang chạy → chỉ đếm/chạy phễu khi crawler đã dừng.
3. Repo vẫn commit 32 file `__pycache__/` và dữ liệu lớn (`raw_data.csv` 18 MB, `clean_data.csv` 14 MB, `data/*.jsonl`); chưa có `.gitignore`. (`.bak*` và `.git copy/` đã xóa 2026-11-20.) Dọn trước khi nộp (G5, K16).
4. **`clean_data.csv`/`raw_data.csv` ở HEAD chứa conflict marker** (commit `02ced55`) → `pd.read_csv` lỗi, `EDA.ipynb` không chạy được. Khôi phục: xem "Repo-health trap" (B0).
5. `README.md` chỉ còn 2 dòng không liên quan (`# Data-mining` + một câu đùa) → viết lại (G2).

## Lỗi cần sửa ở phần cào dữ liệu (kiểm 2026-11-18)

Mỗi lỗi: **vị trí** → hậu quả (có số liệu khi đo được) → *Cách sửa* → *Vì sao*. Sắp theo mức ưu tiên.

### Ưu tiên 1 – mất dữ liệu hoặc hỏng lúc demo

- [ ] **K1. VietnamWorks ghi đè file raw mặc định** – `crawler/vietnamnetworks.py:187` (`--out` mặc định `data/raw/vietnamworks.jsonl`) + `write_jobs` thay file. Demo `--pages 1` sẽ xóa 701 tin cùng `Timestamp` gốc, thay bằng 50 tin. *Cách sửa:* chặn như `itviec.py:99` (`parser.error` nếu `--out` đã tồn tại); demo luôn dùng `--out data/raw/demo_vnw.jsonl`. *Vì sao:* `Timestamp` gốc là bằng chứng audit; mất là không cào lại được đúng thời điểm.
- [ ] **K2. VietnamWorks lỗi giữa chừng là mất hết** – `vietnamnetworks.py:205` gọi `parser.exit` khi một trang lỗi, mà file chỉ được ghi ở dòng 224. Lỗi mạng ở trang 15/16 làm mất 14 trang đã lấy. *Cách sửa:* thử lại 3 lần với `random.uniform` giãn cách; vẫn lỗi thì `break` rồi ghi phần đã có. *Vì sao:* demo trên mạng phòng học dễ chập chờn.
- [ ] **K3. Ghi checkpoint không nguyên tử** – *phần `fetch_detail.flush` đã sửa (file `.tmp` + `replace`); còn* `crawler/base.py:65` (`interactive_scrape` mở `"w"` mỗi 2–3 giây). Ctrl+C đúng lúc ghi để lại file cụt; lần sau `read_jsonl` gặp dòng JSON dở và dừng với lỗi. *Cách sửa:* ghi file tạm cùng thư mục rồi `Path.replace` (mẫu có sẵn ở `clean_salary.main` / `export_data.write_csv`). *Vì sao:* TopCV/LinkedIn đều dừng bằng Ctrl+C, nên lỗi này chắc chắn sẽ xảy ra sớm hay muộn.
- [x] **K4. `fetch_detail` mất tới 199 tin khi dừng** – *đã sửa: `BATCH_SIZE = 20`, `flush()` trong `finally`.* chỉ `flush()` mỗi `BATCH_SIZE = 200` (`fetch_detail.py:24`) và cuối vòng; `KeyboardInterrupt` không được bắt. *Cách sửa:* bọc vòng lặp bằng `try/finally: flush()` (sau khi sửa K3), giảm `BATCH_SIZE` xuống 20. *Vì sao:* chạy TopCV 1.298 tin mất nhiều giờ, phải dừng/tiếp tục được.
- [x] **K5. Trích JD TopCV gần như chắc lấy nhầm cả trang** – *đã sửa: cắt theo mốc "Mô tả công việc" → `TOPCV_ENDS`; đã kiểm 0 JD dính footer.* `extract_topcv` (`fetch_detail.py:232`) chọn `div`/`section` **dài nhất** > 400 ký tự; khối dài nhất thường là khung ngoài chứa header, tin liên quan, footer. Đây là lý do 1.298 tin TopCV vẫn chưa có JD. *Cách sửa:* thử `job_posting_ldjson(soup)` trước (nếu trang TopCV có JSON-LD `JobPosting` như ITviec), nếu không thì chọn selector khối mô tả cụ thể; chạy thử `--site topcv --limit 5` và đọc kết quả bằng mắt trước khi chạy cả 1.298 tin. *Vì sao:* JD rác sẽ sinh skill giả (từ menu, tin gợi ý) cho cụm và luật.

### Ưu tiên 2 – thiếu yêu cầu của đề

- [ ] **K6. TopCV phân trang bằng tay** – `crawler/topcv.py:83` dùng `interactive_scrape`; `fetch_page` (dòng 52) đã viết nhưng không ai gọi; `--pages`, `--limit` không có tác dụng. *Cách sửa:* vòng lặp giống `topdev.main` (`fetch_page` từng trang + `timestamp` + `write_jsonl` + `random.uniform` + dừng khi trang rỗng + chặn `--out` đã tồn tại). *Vì sao:* đề chấm "xử lý phân trang", và crawler sẽ được chạy live; người bấm tay khó giải thích là crawler tự động.
- [~] **K7. Raw thiếu requirements / benefits / nhiều địa điểm** – *phần requirements/benefits xong 2026-11-19: `export_data.jd_sections` cắt JD theo tiêu đề mục mẫu trang → `raw_data.csv` có `requirements_raw` 2.612 / `benefits_raw` 2.556 tin (TopCV 1.290/1.290, ITviec 571/570, VNW 560/562, TopDev 75/75, LinkedIn chỉ 116/59 vì JD tự do); `clean_data.csv` có `benefits` (12 nhóm, `BENEFIT_RE`) + `n_benefits`, trống = không có mục phúc lợi. Còn lại: nhiều địa điểm VNW, `salaryMin/Max` VNW.* Ghi chú gốc: VietnamWorks xin `benefits` trong `retrieveFields` (`vietnamnetworks.py:32`) nhưng `parse_job` bỏ đi; `jobRequirement` bị gộp vào `description` (dòng 121); chỉ giữ `workingLocations[0]` (dòng 103); bỏ `salaryMin/salaryMax/isSalaryVisible`. *Cách sửa:* thêm khóa `requirements`, `benefits`, `locations` (list), `salary_min/max`; `export_data.RAW_COLUMNS` thêm `requirements_raw`, `benefits_raw`. *Vì sao:* đề ghi raw phải có "benefits/requirements"; kế hoạch mục 2 bước 4 có `requirements_raw`, `benefits_raw`.
- [ ] **K8. TopDev cào cả việc không phải IT** – `crawler/topdev.py:12` `LIST_URL = /jobs/search` không lọc ngành: 2.584/2.910 tin là MBBank (đã kiểm URL chứa `mbbank`, cùng bộ tag `Risk Management`…), chỉ 75 tin lọt phạm vi IT. *Cách sửa:* tìm trên web TopDev URL tìm kiếm có lọc IT/kỹ năng (ví dụ theo từ khóa hoặc danh mục), đặt làm `LIST_URL`, cào lại ra file mới. *Vì sao:* TopDev là nguồn thứ hai không cần đăng nhập; demo live mà hiện toàn tin ngân hàng thì khó bảo vệ phạm vi.
- [ ] **K9. `Timestamp` không có múi giờ** – `base.timestamp` dùng `datetime.now()` theo giờ máy, docstring ghi "giờ Việt Nam"; `export_data.iso_timestamp` gắn cứng `+07:00`. Máy đặt múi giờ khác sẽ ghi sai. *Cách sửa:* `datetime.now(timezone(timedelta(hours=7)))` (không dùng `ZoneInfo` vì Windows cần thêm gói `tzdata`), giữ nguyên định dạng chuỗi để dữ liệu cũ vẫn đọc được. *Vì sao:* kế hoạch yêu cầu "ISO 8601 có múi giờ, ghi lúc lấy".

### Ưu tiên 3 – chất lượng dữ liệu raw

- [ ] **K10. TopCV dính chữ** – *phần tên công ty đã vá ở clean (`lam_sach.clean_company` bỏ tiền tố "Pro"); raw và crawler chưa sửa.* `topcv.py:46` (và các trường khác) dùng `get_text(strip=True)` nên các thẻ con dính nhau: 2.426/2.426 `posted_at` có dạng `"Đăng2 tuần trước"`, `"Đănghôm nay"`; 170/1.298 tên công ty TopCV trong tập IT dính huy hiệu ("ProTập đoàn FPT"). *Cách sửa:* `get_text(" ", strip=True)` cho mọi trường (giống `itviec.parse_card` dòng 40). *Vì sao:* raw phải là văn bản gốc trên trang, không phải lỗi parse.
- [ ] **K11. TopCV không lấy tag kỹ năng** – `parse_cards` không có khóa `skills`, nên `filter_it` quyết định TopCV chỉ bằng title (278 tin `ambiguous`). *Cách sửa:* mở một card TopCV, nếu có tag kỹ năng thì thêm selector. *Vì sao:* tag giúp phân biệt "Kỹ thuật IT" với tin không IT.
- [ ] **K12. ITviec/TopDev/TopCV không thử lại, ITviec dừng hẳn ở trang cuối** – `itviec.py:85` `wait_for_selector("div.job-card")` ném `TimeoutError` khi trang rỗng hoặc gặp Cloudflare, nên không tới được `if not rows: break`; mọi `page.goto` không có retry (chỉ `linkedin.py` có). *Cách sửa:* bắt `PlaywrightTimeoutError` → coi là trang rỗng; thêm vòng 3 lần thử cho `goto` (giống `linkedin.py:109`). *Vì sao:* demo không được kết thúc bằng traceback.
- [ ] **K13. LinkedIn: cần đăng nhập, title đôi khi lẫn chữ thừa** – title lấy từ `aria-label` tiếng Việt ("Hủy bỏ việc làm …", `linkedin.py:35`), giao diện tiếng Anh thì dùng `paras[0]` kèm chữ thừa (13 tin có "with verification"…); `--scrolls`, `--headless` không có tác dụng thật. *Cách sửa:* không dùng LinkedIn để demo; ghi rõ trong báo cáo là nguồn phụ cần đăng nhập; lọc chữ "with verification" khỏi title. *Vì sao:* demo phải chạy được trên máy khác mà không cần tài khoản; cookie trong `data/linkedin-profile` không được nộp.
- [x] **K14. `posted_at` là thời gian tương đối** – *xong 2026-11-19: `clean_data.csv` có `posted_date` + `posted_date_source` cho 3.216/3.216 tin: `field` 1.894 (date_posted gốc của ITviec/TopDev/VNW/LinkedIn), `relative` 1.322 (TopCV + 24 ITviec, ước lượng). Tuổi tin median 14–20 ngày; 81 tin > 90 ngày (LinkedIn `createdAt` tới 589 ngày, TopDev 1 tin 2020) → lọc khi phân tích theo thời gian. ITviec: 208/574 tin có ngày gốc sớm hơn chuỗi "x days ago" ≥ 2 ngày (tin làm mới).* "5 days ago", "Đăng2 tuần trước"; TopCV không có `date_posted`. *Cách sửa (tùy chọn):* trong `export_data`, ước lượng `posted_date ≈ Timestamp − n ngày/tuần`, ghi rõ là ước lượng. *Vì sao:* cần nếu muốn phân tích theo thời gian; không bắt buộc theo đề.
- [x] **K15. Gộp nhầm tin khác địa điểm** – *xong 2026-11-20 (code + dry-run, chưa chạy lại phễu): `key_of` thêm `city_key(location)` = thành phố chuẩn hóa bởi `lam_sach.parse_cities` (không dùng chuỗi `location` thô vì LinkedIn ghi "Ho Chi Minh City, Vietnam (On-site)" / "…Metropolitan Area" cho cùng một nơi; thành phố "Khác" dùng chính chuỗi địa điểm). Dry-run trên `data/raw`: 28 nhóm từng bị gộp qua nhiều địa điểm; `dedup` 7.291 → **7.308** (+17: LinkedIn 10, TopCV 5, ITviec 1, VietnamWorks 1); `dedup.jsonl`, `it.jsonl`, `full.jsonl` chưa đổi. Phải chạy lại phễu (B1) để 17 tin mới vào `clean_data.csv`.* Ghi chú gốc: `pipline/duplicate.py` gộp cùng `site + company + title` kể cả khác `location` (MBBank đăng cùng chức danh cho nhiều chi nhánh). *Cách sửa:* thêm `location` vào `key_of`. *Vì sao:* kế hoạch yêu cầu "giữ riêng tin khác địa điểm"; ảnh hưởng số tin theo thành phố.
- [~] **K16. Dọn code chết trước khi nộp** – *2026-11-20: đã xóa `api_key_vietnamnetwork.py` và `dump_linkedin.py`; còn `browser.webkit_context` (không ai gọi) và import thừa `parse_qs`, `urlsplit`, `PlaywrightError` ở `itviec.py`.* Ghi chú gốc: `browser.webkit_context` không ai dùng; `api_key_vietnamnetwork.py` thực ra là công cụ in danh sách key của API (tên gây hiểu nhầm); `dump_linkedin.py` là công cụ debug; `itviec.py` import thừa `parse_qs`, `urlsplit`, `PlaywrightError`. *Cách sửa:* xóa hoặc chuyển vào `tools/`, đổi tên `inspect_vnw_api.py`. *Vì sao:* vấn đáp hỏi ngẫu nhiên bất kỳ file nào; file không dùng mà không giải thích được sẽ bị trừ điểm.

## Cột `clean_data.csv` cần lưu ý khi EDA (41 cột, số liệu 2026-11-19)

| Cột | Ý nghĩa | Lưu ý |
|---|---|---|
| `job_uid` | `site-sha1(url)[:10]`, khóa nối với `raw_data.csv` | ổn định giữa các lần export |
| `job_group_id`, `is_primary` | cùng việc làm đăng ở nhiều nguồn (`group_jobs`); 3.135 nhóm, 67 nhóm > 1 dòng | lọc `is_primary` khi đếm việc làm; `groups=job_group_id` khi chia train/test (F3) |
| `source`, `URL_Goc`, `Timestamp` | nguồn, link gốc, thời điểm cào (ISO +07:00) | lương: TopCV 518, ITviec 129, VNW 105, TopDev 10, LinkedIn 5 → so sánh lương thiên về TopCV |
| `posted_date`, `posted_date_source` | ngày đăng YYYY-MM-DD; `field` 1.885 (ngày gốc của nguồn) / `relative` 1.319 (TopCV + 24 ITviec, **ước lượng** Timestamp − "x tuần trước") | 81 tin đăng > 90 ngày trước khi cào (LinkedIn `createdAt` tới 589 ngày) → lọc khi phân tích theo thời gian |
| `title`, `company` | gom khoảng trắng; company bỏ huy hiệu "Pro" TopCV | `company` trống 1 tin (VNW) |
| `it_decision`, `it_decision_source`, `title_role` | keep 2.938 / ambiguous 266; `filter` / `jd_tech` / `manual`; nhóm vai trò từ title (`software`, `data_ai`, `pm_po`, `qa_test`, `generic`…) | `pm_po` (187) do `lam_sach.is_pm_po` ghi đè; chạy lại bản chỉ `keep` để kiểm độ nhạy |
| `city`, `cities` | TP.HCM 1.569, Hà Nội 1.391, Khác 189, Đà Nẵng 40, trống 15 | tin nhiều nơi chỉ tính cho `city`; dùng `cities` + `explode` nếu muốn đếm mọi nơi |
| `work_mode`, `work_mode_source` | Onsite/Hybrid/Remote; `field` 598 / `jd` 187 / `title` 24 | 75% trống; Onsite gần như chỉ ITviec → không so sánh giữa nguồn |
| `exp_min_years`, `exp_max_years`, `exp_source` | số năm; `field` 1.383 / `jd` 1.326 | `exp_max` thường trống ("3+ years"); 495 tin không có |
| `seniority`, `seniority_source`, `is_intern` | Junior 891 / Senior 812 / Middle 600 / Lead 413 / Fresher 248 / trống 240; nguồn `years` 1.702, `title` 1.238, `level_field` 24 | `years` → **leakage** nếu phân lớp dùng lại số năm. Manager/Head/Director/C-level gộp vào Lead; PM/PO chỉ Lead khi title có Lead/Head… `is_intern` 109 tin (thực tập/CTV/trainee) |
| `Luong_Min`, `Luong_Max`, `Luong_TB` | VND/tháng; TB = (min+max)/2 chỉ khi đủ 2 cận | `min_only` 12, `max_only` 153 không có TB; thương lượng/ẩn/missing/invalid = trống, không phải 0 |
| `salary_status` | closed_range 767 / min_only 12 / max_only 153 / negotiable 1.557 / hidden 24 / missing 674 (LinkedIn) / invalid 6 / unknown 11 | tính **tỷ lệ công khai lương** theo nguồn/thành phố; loại `missing` khỏi mẫu số |
| `salary_currency_orig`, `salary_source` | VND 745 / USD 193; `salary` 2.553 / `salary_detail` 634 (JSON-LD) / `jd` 17 | `jd` = khoảng lấy từ JD, có thể là tổng thu nhập |
| `salary_period_assumed` | True = TopCV, kỳ trả "tháng" là giả định | 529 tin; lọc `== False` để kiểm độ nhạy |
| `tech`, `keywords`, `n_tech`, `n_keywords` | skill chuẩn hóa (JSON array) | 430 tin `n_tech = 0` (420 có JD: BA/PM/QC… không ghi công nghệ) → mẫu số top skill = tin `has_jd` (3.172) |
| `languages`, `n_languages` | ngôn ngữ JD **có nhắc** (English/Japanese/Korean/Chinese), không phải "bắt buộc" | trống khi không có JD; `[]`/0 khi JD không nhắc |
| `benefits`, `n_benefits` | nhóm phúc lợi trong `benefits_raw` (`BENEFIT_RE`, 12 nhóm) | trống = không có mục phúc lợi (không biết); 2.545 tin có |
| `has_jd`, `jd_chars`, `description` | cờ JD, độ dài, JD đã gom khoảng trắng | chưa bỏ stop word; 0 tin có thẻ HTML |

Đọc list: `df["tech"] = df["tech"].apply(json.loads)`.

---

## Việc còn lại – checklist chi tiết

Mỗi task: **làm gì** → *Cách làm* → *Vì sao*. Tích `[x]` khi xong và ghi số liệu thật bên cạnh.

### A. Làm sạch còn lại (2.1 – TV2)

- [x] **A1. Lấy JD TopCV** – *xong: 1.290/1.298 có JD, đã chạy lại `extract_tech_skill_` → `clean_salary` → `export_data`.* *Cách làm:* `python -m pipline.fetch_detail --in data/it.jsonl --site topcv` (chạy có cửa sổ nếu gặp Cloudflare), rồi chạy lại `extract_tech_skill_` → `clean_salary` → `export_data`. Mở 10 JD TopCV xem có dính khối quảng cáo của `extract_topcv` (lấy `div` dài nhất) không. *Vì sao:* TopCV là 40% tập IT và nguồn lương công khai lớn nhất; thiếu JD thì mất cho kỹ năng, cụm và luật.
- [x] **A2. Chốt chiến lược lương TopCV không ghi kỳ trả** – *xong (code + test): `salary_period_assumed`, `Luong_TB` 227 → 755. **Còn thiếu bằng chứng**: chưa mở 5–10 tin gốc trên TopCV để xác nhận là lương tháng; lý do hiện ghi trong docstring là phân bố số (cận trên trung vị 25M, tối đa 85M).* *Cách làm:* mở 5–10 tin "15 - 20 triệu" trên trang gốc; nếu đều là lương tháng, cho `clean_salary.clean_row` truyền `period_hint="month"` khi `site == "topcv"`, thêm test, ghi giả định vào báo cáo. *Vì sao:* nâng số tin có lương từ 227 lên khoảng 860, đủ n cho lương theo cấp bậc và theo thành phố; quyết định có bằng chứng thì không vi phạm nguyên tắc "không tự đoán kỳ trả".
- [x] **A3. Kiểm `experience_months` ITviec (10/37/61)** – *xong 2026-11-19: đối chiếu JD (201 tin mốc 10: JD ghi 1–5 năm, 0 tin 0 năm) → `parse_experience` dùng JD trước, mốc tháng sau và `round(m/12)` (10 → 1 năm). ITviec Fresher 168 → 28; median lương (`salary_period_assumed == False`) Fresher 5,6M (n=6) < Junior 25M (66) < Middle 31,3M (52) < Senior 42,5M (55) < Lead 62,5M (21). Chưa mở trang gốc để kiểm tay.* *Cách làm:* mở 5 tin mỗi giá trị, so với dòng "x năm kinh nghiệm" trên trang; nếu 10 ứng với "1+ năm", sửa `parse_experience` (ví dụ làm tròn lên `ceil(m/12)`) và test. *Vì sao:* 10 tháng hiện thành Fresher, làm nhãn và biểu đồ lương theo cấp bậc bị sai (Fresher > Junior).
- [ ] **A4. Kiểm lại nhãn seniority bằng mắt** – *Cách làm:* lấy ngẫu nhiên 30 tin (10 mỗi `seniority_source`), ghi đúng/sai; xem các title có 2 mức ("Junior/Middle" đang lấy mức cao). *Vì sao:* đề hỏi lương theo cấp bậc và phân lớp theo cấp bậc; cần một con số độ chính xác để bảo vệ.
- [ ] **A5. Stop words VI/EN cho văn bản JD** – *Cách làm:* trong notebook tạo `jd_clean`: chữ thường, bỏ dấu câu/số, bỏ stop word từ một file nhỏ tự viết `data/stopwords_vi.txt` (≈100 từ: "và, của, các, có, được, trong, cho, với, làm, việc…") + `sklearn.feature_extraction.text.ENGLISH_STOP_WORDS`. Giữ nguyên token đặc biệt `C++`, `C#`, `.NET`, `Node.js` (tách token bằng khoảng trắng, không bằng `\W`). *Vì sao:* đề yêu cầu; danh sách tự viết giải thích được khi vấn đáp, không thêm thư viện tách từ tiếng Việt.
- [ ] **A6. Xác nhận bước strip HTML** – *Cách làm:* một ô notebook đếm `description_raw` chứa `<tag>`/`&nbsp;` (hiện 0), nếu có thì `BeautifulSoup(x, "lxml").get_text(" ")`. *Vì sao:* đề chấm bước này; chứng minh bằng số thay vì bỏ qua im lặng.
- [ ] **A7. Ma trận one-hot kỹ năng** – *Cách làm:* `MultiLabelBinarizer().fit_transform(df.tech)`; chỉ giữ skill xuất hiện ở ≥ 10 tin; lưu tên cột. *Vì sao:* đầu vào chung cho cụm (2.3), luật (2.4), phân lớp (2.5); lọc skill hiếm giảm nhiễu và số chiều.
- [ ] **A8. (Nâng cao) Đo chất lượng trích xuất** – *Cách làm:* 30 chuỗi lương đủ dạng gắn kỳ vọng tay → % đúng; 20 JD gắn skill tay → precision/recall của từ điển, kèm 1–2 lỗi ví dụ (C/R). *Vì sao:* kế hoạch mục 5.2; chứng minh regex/từ điển đáng tin bằng số.

### B. Khóa clean v1 (TV2 + TV1)

- [ ] **B1. Chạy lại phễu một lần sau khi sửa crawler** – *Cách làm:* dừng mọi crawler, sửa K1–K8, rồi chạy `duplicate` → `filter_it` → `fetch_detail` (chỉ tin mới/thiếu JD) → `extract_tech_skill_` → `clean_salary` → `export_data`; ghi số từng nấc. *Vì sao:* `dedup.jsonl` hiện thiếu 48 tin LinkedIn mới (JD TopCV đã có); khóa clean v1 trên dữ liệu cũ thì sau phải làm lại EDA.
- [x] **B2. `canonical_group` – khử trùng chéo nguồn** – *xong 2026-11-19 bằng `pipline/group_jobs.py` (rapidfuzz, cột `job_group_id` + `is_primary`): 3.135 nhóm, 67 nhóm > 1 nguồn (136 dòng, `data/duplicate_groups.csv`); chưa kiểm tay.* Ghi chú gốc: *Cách làm:* thêm cột trong `export_data.py` hoặc notebook: `normalize(company) + "|" + normalize(title đã bỏ từ cấp bậc)`; đếm số nhóm có > 1 nguồn. *Vì sao:* cùng tin đăng trên ITviec và LinkedIn mà rơi vào cả train và test là rò rỉ; EDA "số tin" cũng bị đếm đôi.
- [ ] **B3. Bảng chất lượng theo nguồn** – *Cách làm:* `df.groupby("source").agg(n, %has_jd, %Luong_TB, %seniority, %exp, median n_tech)`. *Vì sao:* kế hoạch yêu cầu báo thiếu dữ liệu theo nguồn; giải thích vì sao lương chỉ đại diện cho 2 nguồn.
- [ ] **B4. Kiểm truy vết** – *Cách làm:* mọi `job_uid` của clean có trong raw; mở ngẫu nhiên 20 `URL_Goc` (5/nguồn) so với nội dung, ghi URL hết hạn. *Vì sao:* giảng viên sẽ làm đúng việc này khi chấm.
- [ ] **B0. Sửa repo hỏng (làm trước mọi việc khác)** – *Cách làm:* `git checkout 7e5d97d -- clean_data.csv raw_data.csv` (hoặc chạy lại `python -m pipline.export_data`), kiểm `grep -c '^<<<<<<<' clean_data.csv raw_data.csv` = 0 và `pd.read_csv` ra (3204, 41) / (3204, 21); thêm `.gitattributes` (`*.csv -text`, `*.jsonl -text`) và `.gitignore` (`__pycache__/`, `data/linkedin-profile*`) để lần merge sau không đổi CRLF cả file; trước khi `pull`/`merge`, báo cả nhóm dùng cùng một bản. *Vì sao:* hiện không ai đọc được dữ liệu đã nộp; CRLF/LF làm git coi cả 18 MB là "đổi hết", nên hai người cùng sửa một CSV là conflict chắc chắn.
- [ ] **B5. Khóa phiên bản** – *Cách làm:* ghi vào báo cáo/notebook: ngày khóa, số dòng, `hashlib.md5` của `clean_data.csv`; sau đó mọi người chỉ đọc file này. *Vì sao:* EDA, cụm, luật, phân lớp chạy song song phải dùng cùng mẫu số.
- [ ] **B6. Từ điển cột** – *Cách làm:* chép bảng "Cột `clean_data.csv`" ở trên vào báo cáo chương 2, thêm cột kiểu dữ liệu. *Vì sao:* deliverable "từ điển trường kèm bản dữ liệu".

### C. EDA (2.2 – TV2)

- [ ] **C1. Lương theo cấp bậc** – *Cách làm:* boxplot `Luong_TB/1e6` theo `seniority` thứ tự Fresher → Lead, ghi `n=` trên mỗi hộp; bảng median + IQR + n có lương + n toàn nhóm + % công khai. *Vì sao:* lương lệch phải, có ngoại lai → median/IQR bền hơn mean; ghi n để không suy rộng từ nhóm nhỏ.
- [ ] **C2. Top 15 kỹ năng** – *Cách làm:* `explode("tech")`, đếm, chia cho số tin `has_jd` (mẫu số), bar ngang theo %. Hiện đứng đầu (3.172 tin có JD, 2026-11-19): Python 931, SQL 820, Docker 550, Java 526, Linux 508, Git 505, Kubernetes 464, REST API 449, PostgreSQL 377, JavaScript 324, Jira 311, React 279, MySQL 278, ERP 272, C# 265. Jira/ERP thuộc `GENERAL_TOOLS` (có cả ở tin không IT) → nói rõ có giữ chúng trong top 15 hay không. *Vì sao:* tin không JD có `tech` rỗng; chia cho toàn bộ 3.204 tin sẽ làm tỷ lệ thấp giả.
- [ ] **C3. So sánh vùng** – *Cách làm:* (a) số tin theo `city`; (b) median lương theo city kèm n; (c) top 10 skill theo HN vs HCM (tỷ lệ trong vùng). Ghi rõ quy ước tin nhiều nơi. *Vì sao:* đề yêu cầu; Đà Nẵng có rất ít tin lương → phải nói "chưa đủ mẫu" thay vì kết luận.
- [ ] **C4. Tỷ lệ công khai lương** – *Cách làm:* stacked bar `salary_status` theo `source` và theo `city`. *Vì sao:* cho thấy lương công khai là mẫu thiên lệch, chống suy rộng (kế hoạch mục 5.2).
- [ ] **C5. Ngoại lai lương** – *Cách làm:* liệt kê `Luong_TB` < 5M hoặc > 150M kèm `URL_Goc`, mở kiểm từng tin. *Vì sao:* lỗi regex (nhầm năm/tháng, USD) hay hiện ở đuôi phân phối.
- [ ] **C6. (Thêm) Kỹ năng theo nhóm vai trò** – *Cách làm:* heatmap tỷ lệ top 15 skill × `title_role`. *Vì sao:* tạo giả thuyết trước khi gom cụm và kiểm lại tên cụm sau này.

### D. Gom cụm (2.3 – TV3)

- [ ] **D1. Chọn tập và đặc trưng** – *Cách làm:* tin có `n_tech ≥ 2` (2.397 tin; 2.338 nếu chỉ `is_primary`); đặc trưng = one-hot `tech` (A7), tùy chọn thêm `keywords`. Báo số tin bị loại và lý do. *Vì sao:* vector rỗng không có nghĩa "không cần kỹ năng" mà là thiếu JD; nhị phân cùng thang đo nên không cần chuẩn hóa.
- [ ] **D2. Elbow + Silhouette** – *Cách làm:* `KMeans(n_clusters=k, n_init=10, random_state=42)` với k = 1…10 (inertia), `silhouette_score` với k = 2…10; vẽ cạnh nhau. *Vì sao:* đề bắt buộc cả hai; Elbow thường mờ với dữ liệu nhị phân nên cần Silhouette làm tiêu chí thứ hai.
- [ ] **D3. Chốt K** – *Cách làm:* chọn K theo Silhouette cao + khuỷu + mỗi cụm ≥ 5% số tin + đặt tên được; nếu hai tiêu chí khác nhau, viết vì sao chọn. *Vì sao:* vấn đáp sẽ hỏi "Elbow và Silhouette gợi ý khác nhau thì làm sao".
- [ ] **D4. Chân dung và đặt tên cụm** – *Cách làm:* mỗi cụm: n, %, top skill theo **lift** = P(skill | cụm) / P(skill), `title_role` phổ biến, median lương (nếu có), 1–2 tin mẫu kèm URL. Đặt tên sau khi xem số (ví dụ "Backend Java/Spring", "Data/AI Python", "DevOps/Cloud", "Frontend JS", ".NET/C#"). *Vì sao:* Python/SQL/Git có mặt khắp nơi; tần suất thô làm mọi cụm trông giống nhau, lift cho thấy cái đặc trưng.
- [ ] **D5. Độ ổn định** – *Cách làm:* chạy 3 seed, so `adjusted_rand_score` giữa các lần và Silhouette. *Vì sao:* kế hoạch mục 5.3; chứng minh cụm không phải ngẫu nhiên.
- [ ] **D6. Hình 2D** – *Cách làm:* `PCA(2)` tô màu theo cụm (chỉ để minh họa). *Vì sao:* slide dễ hiểu; nói rõ PCA chỉ để vẽ, không dùng để chọn K.

### E. Luật kết hợp (2.4 – TV3)

- [ ] **E1. Giỏ hàng** – *Cách làm:* mỗi tin `has_jd` có ≥ 2 skill là một giỏ (`tech`, thử thêm `keywords`). `mlxtend`: `TransactionEncoder` → `fpgrowth(min_support=0.01)` → `association_rules`. Nếu không muốn thêm thư viện: tự đếm cặp 2 skill bằng `Counter` (chỉ luật 1 → 1, dễ giải thích). *Vì sao:* FP-Growth nhanh hơn Apriori và cho cùng kết quả; giỏ có 1 skill không sinh luật.
- [ ] **E2. Lọc luật** – *Cách làm:* support ≥ 1% **và** ≥ 10 tin, confidence ≥ 0,5, **lift > 1,2**, có cột conviction; lưu số đếm tử/mẫu. *Vì sao:* đề bắt buộc lift > 1,2 và conviction; số đếm cho phép tính tay khi vấn đáp.
- [ ] **E3. Bỏ luật dư thừa** – *Cách làm:* bỏ luật có vế trái là tập cha của luật khác cùng vế phải mà confidence tăng < 0,05. *Vì sao:* bảng gọn, chỉ còn luật mang thông tin mới.
- [ ] **E4. Chỉ ra luật gây hiểu nhầm** – *Cách làm:* (a) confidence cao nhưng lift ≈ 1 vì vế phải phổ biến (`X → Python`, `X → SQL`); (b) lift cao nhưng support rất nhỏ; (c) luật hiển nhiên do công nghệ phụ thuộc nhau (`Spring Boot → Java`, `Kubernetes → Docker`, `Next.js → React`). *Vì sao:* đề yêu cầu cảnh báo luật gây hiểu nhầm; đồng xuất hiện không phải quan hệ nhân quả.
- [ ] **E5. Tính tay một luật** – *Cách làm:* đếm trực tiếp trên DataFrame: n(A), n(B), n(A∩B) → support, confidence, lift, conviction; so với mlxtend. *Vì sao:* kế hoạch yêu cầu TV3 tính tay khi bảo vệ.
- [ ] **E6. Độ bền** – *Cách làm:* chạy lại với support 0,5% và 2%, hoặc tách theo nguồn (ITviec vs LinkedIn); đánh dấu luật chỉ có ở một nguồn. *Vì sao:* kế hoạch mục 5.3; luật chỉ ở một nguồn có thể do cách nguồn đó gắn tag.

### F. Phân lớp (2.5 – TV4)

- [ ] **F1. Chốt bài toán theo n thật** – *Cách làm:* hiện (2026-11-19) cấp bậc có Junior 891 / Middle 600 / Senior 812 (đủ ≥ 50/lớp), → chọn **Junior/Middle/Senior**, bỏ Fresher/Lead/NA. Sau A2, khoảng lương cũng đủ n: `< 15M` 169 / `15–30M` 363 / `> 30M` 235 (767 tin, 69% là TopCV giả định tháng) → có thể làm thêm như bài toán phụ, nhưng phải báo kết quả riêng cho tin `salary_period_assumed == False`. *Vì sao:* kế hoạch: chọn mục tiêu theo nhãn có thật, không chọn theo điểm test.
- [ ] **F2. Chặn leakage** – *Cách làm:* đặc trưng = one-hot `tech` + `keywords`, `n_tech`, `city`, `source`, `title_role`. **Không** dùng `title`, `exp_min_years`, `exp_max_years`, `seniority_source`, `description` thô (chứa "3 năm kinh nghiệm", "Senior"). *Vì sao:* nhãn sinh từ title (1.307 tin) và từ số năm (1.653 tin); đưa lại chúng vào đầu vào thì mô hình chỉ học lại luật gán nhãn.
- [ ] **F3. Chia train/test theo nhóm** – *Cách làm:* `GroupShuffleSplit(test_size=0.2, random_state=42)` với `groups=job_group_id` (B2, đã có trong `clean_data.csv`); kiểm phân bố lớp ở hai phía. *Vì sao:* tin đăng lại/đăng chéo không được nằm ở cả hai phía.
- [ ] **F4. Mốc so sánh** – *Cách làm:* `DummyClassifier(strategy="most_frequent")`. *Vì sao:* nếu mô hình chỉ hơn mốc này chút ít thì phải nói thẳng.
- [ ] **F5. Decision Tree + `ccp_alpha`** – *Cách làm:* trong `Pipeline` (OneHotEncoder cho cột phân loại); `cost_complexity_pruning_path` trên train để lấy dãy alpha; `GridSearchCV(ccp_alpha, max_depth, class_weight="balanced", cv=GroupKFold(5), scoring="f1_macro")`. Báo train vs validation **trước và sau** cắt tỉa; `plot_tree(max_depth=3)`. *Vì sao:* đề bắt buộc; encoder nằm trong Pipeline nên chỉ fit trên fold train.
- [ ] **F6. Mô hình đối sánh** – *Cách làm:* `LogisticRegression(class_weight="balanced", max_iter=1000)` (đọc hệ số được) và/hoặc `RandomForestClassifier(random_state=42)`, cùng split và CV. *Vì sao:* đề cần ≥ 1 mô hình đối sánh; LR dễ giải thích, RF là mốc mạnh.
- [ ] **F7. Đánh giá** – *Cách làm:* `confusion_matrix`, `classification_report` (precision/recall từng lớp), macro F1, n mỗi lớp. *Vì sao:* lớp lệch → accuracy đánh lừa, macro F1 coi mỗi lớp ngang nhau.
- [ ] **F8. Phân tích lỗi** – *Cách làm:* 3–5 tin dự đoán sai kèm URL, skill, nhãn thật/dự đoán, giải thích (ví dụ Junior ↔ Middle chung bộ skill; nhãn `years` từ JD bị sai). Thêm feature importance của cây. *Vì sao:* đề yêu cầu phân tích lỗi; cho thấy giới hạn là chỉ dùng skill.
- [ ] **F9. (Nâng cao) Kiểm tổng quát theo nguồn** – *Cách làm:* train trên các nguồn còn lại, test riêng một nguồn đủ nhãn (ví dụ TopCV), báo n. *Vì sao:* kế hoạch mục 5.4.

### G. Deliverable và demo (TV1 + TV4)

- [ ] **G1. `scraper.py`** – *Cách làm:* một file mỏng ở gốc gọi `main()` của từng crawler theo tham số (`python scraper.py itviec --pages 2 --out data/raw/demo.jsonl`). *Vì sao:* đề đòi đúng tên file; giữ nguyên code `crawler/` đã chạy ổn.
- [ ] **G2. `requirements.txt` + README lệnh chạy** – *Cách làm:* `playwright`, `beautifulsoup4`, `lxml`, `requests`, `tqdm`, `rapidfuzz`, `pandas`, `scikit-learn`, `matplotlib`, `mlxtend` (nếu dùng); thêm bước `playwright install chrome`. *Vì sao:* deliverable bắt buộc; máy thứ hai phải chạy lại được.
- [ ] **G3. Notebook `NhomXX_MiningPipeline.ipynb`** – *Cách làm:* đọc `clean_data.csv` (đường dẫn tương đối) → kiểm data → EDA → cụm → luật → phân lớp → kết luận; `random_state=42` mọi nơi; mỗi hình ghi n và điều kiện lọc; `Restart Kernel → Run All` trên máy thứ hai. *Vì sao:* đề chấm notebook chạy trọn không lỗi.
- [ ] **G4. Tập demo live** – *Cách làm:* `python -m crawler.itviec --pages 1 --limit 10 --headless --out data/raw/demo_itviec.jsonl` và `fetch_detail` 2–3 tin; xóa file demo cũ trước. Không demo LinkedIn (cần đăng nhập). *Vì sao:* demo chạy thật trước giảng viên; ITviec/VietnamWorks không cần đăng nhập.
- [~] **G5. Đóng gói sạch** – *đã xóa `.bak*`, `.git copy/`, `dump_linkedin.py` (2026-11-20); còn 32 file `__pycache__` đang được commit (`git rm -r --cached`).* *Cách làm:* không nộp `data/linkedin-profile*`, `data/public-profile`, `data/linkedin_dump.html`, `__pycache__`. *Vì sao:* chứa cookie/phiên đăng nhập; file thừa bị hỏi khi vấn đáp.
- [ ] **G6. Cập nhật `KE_HOACH_BAI_TAP_LON_NHOM_4.md`** – *file không có trong repo này: đưa vào repo trước.* *Cách làm:* sửa phạm vi thành "mọi vị trí IT", cập nhật phễu số liệu. *Vì sao:* báo cáo và kế hoạch phải khớp số với notebook.
