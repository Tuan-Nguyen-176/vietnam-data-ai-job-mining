## Tổng quan bước 2.3 — Gom cụm kỹ năng (K-Means)

- Chia các tin tuyển dụng IT thành những nhóm có bộ kỹ năng gần nhau, rồi đặt tên và mô tả từng nhóm.

- Phần kiểm tra độ tin cậy cho thấy cái gì ổn định (tên cụm) và cái gì dao động khi chạy lại (kích thước cụm).

**Đầu vào:** `clean_data_processed.csv` (bước 2.1, cột `skills`)  
**Đầu ra:** 8 cụm đã đặt tên, bảng chân dung cụm và `data/cluster_assignments.csv` (dùng cho 2.4, 2.5).

### Ý tưởng trong ba câu

1. Mỗi tin là một dòng 0/1: tin có (1) hay không có (0) từng kỹ năng.
2. K-Means gom các tin có bộ kỹ năng gần nhau vào cùng một cụm.
3. Tên cụm không đặt theo cảm tính mà dựa vào những kỹ năng cụm đó nhắc nhiều hơn mức bình thường (lift).

### Ví dụ: một tin đi qua bước này như thế nào

    Tin:           Senior .NET Developer (LinkedIn)
    skills:        .NET, ASP.NET, AWS, C#, GitHub, PostgreSQL, REST API, React, SQL
    vector 0/1:    143 cột kỹ năng; các cột trên = 1, còn lại (Spring Boot, Kafka...) = 0
    kết quả:       cụm "Frontend và Web", Silhouette −0,0010

Silhouette sát 0 nghĩa là tin nằm gần như đúng ranh giới: nó có React (nét Frontend) nhưng cũng có ASP.NET, REST API và PostgreSQL (nét Backend). Một số tin kiểu này là lý do cụm Frontend và Web kém chặt nhất.

## Kết quả

Mẫu số: 2.843 tin IT có JD → **2.218 tin được gom cụm** (143 kỹ năng). 175 tin không trích được kỹ năng và 450 tin còn dưới 3 kỹ năng được giữ riêng, không gom.

| Cụm | Tên | Số tin | % | Kỹ năng đặc trưng (lift) | Số tin khi chạy lại 20 hạt giống |
| --: | --- | -----: | -: | ------------------------ | -------------------------------: |
| 1 | Frontend và Web | 363 | 16% | CSS, HTML, JavaScript, React, C# | 343 – 411 |
| 2 | Dữ liệu doanh nghiệp (SQL, BI, ERP) | 339 | 15% | Power BI, ERP, SQL | 248 – 354 |
| 3 | Backend Java (Spring, Microservices) | 331 | 15% | Spring Boot, Redis, Kafka, Microservices | 299 – 375 |
| 4 | DevOps / Cloud | 323 | 15% | Ansible, Terraform, Jenkins, Kubernetes | 273 – 337 |
| 5 | Data Science / ML / LLM | 296 | 13% | Machine Learning, LLM, Python | 239 – 388 |
| 6 | Hệ thống, mạng và bảo mật | 211 | 10% | Cisco, Firewall, VMware, Windows Server | 193 – 217 |
| 7 | Quy trình Agile / Scrum | 206 | 9% | Scrum, Jira, Agile | 193 – 211 |
| 8 | C / C++ và Linux | 149 | 7% | C, C++, Linux | 147 – 173 |

Cột cuối cho thấy *kích thước cụm chỉ nên đọc là "khoảng"*: cùng dữ liệu, đổi hạt giống ngẫu nhiên thì số tin mỗi cụm đổi như vậy (xem 2.3.5).

### 2.3.0 — Cấu hình, đọc dữ liệu, hàm dùng chung

Mọi tham số (ngưỡng, K, số hạt giống…) nằm trong **một ô duy nhất**; muốn thử giá trị khác chỉ sửa ở đó. Các hàm dùng chung (`build_matrix`, `evaluate_k`, `describe_clusters`, `name_clusters`) gom vào một ô để các mục sau chỉ việc gọi. Ô đầu in phiên bản scikit-learn, numpy, pandas vì kết quả K-Means phụ thuộc phiên bản.

### 2.3.1 — Chọn đặc trưng, mẫu số và chuẩn hóa vector

- **Mẫu số:** tin IT có JD. Tin có JD nhưng không trích được kỹ năng nào (175 tin) không có gì để so sánh với tin khác, nên được báo riêng chứ không gom.

- **Hai ngưỡng:** mỗi tin phải có từ 3 kỹ năng trở lên, mỗi kỹ năng phải có ở từ 10 tin trở lên. Lọc lặp lại cho đến khi cả hai cùng đúng → còn 2.218 tin × 143 kỹ năng.

- **Chuẩn hóa độ dài (L2):** chia mỗi vector cho độ dài của nó, để K-Means không chia theo "tin ghi nhiều hay ít kỹ năng". Bằng số: phần biến thiên của "số kỹ năng mỗi tin" do cụm giải thích giảm từ khoảng 0,5 xuống 0,3.

### 2.3.2 — Chọn K: Elbow, Silhouette và độ ổn định

Thử K từ 2 đến 12. Elbow không có khuỷu rõ (mỗi bước giảm 3,9% → 1,4%) nên chỉ để quan sát. Quy tắc gợi ý K, đặt trước khi xem kết quả:

1. Mỗi cụm có ít nhất 5% số tin.
2. ARI trung bình từ 0,80 trở lên khi chạy lại với 5 hạt giống khác.
3. Trong các K còn lại, K có Silhouette cao nhất được gợi ý.

Các K đạt quy tắc là 2, 3, 6, 7, 8; quy tắc gợi ý K = 8 (Silhouette 0,074).

**K được chốt cố định `K_FINAL = 8`, quy tắc chỉ còn là gợi ý.** Lý do là một lỗi đã gặp: khi chạy ở máy khác, quy tắc có thể ra K = 7, cụm Backend Java biến mất, mà các `assert` vẫn qua nên không ai biết. Nguyên nhân là Silhouette của K = 6, 7, 8 chỉ chênh nhau 0,002–0,004 (ngang mức dao động giữa các hạt giống), còn ARI của K = 8 chỉ hơn ngưỡng 0,80 một chút. Giờ notebook in cảnh báo nếu quy tắc gợi ý K khác `K_FINAL`, thay vì lặng lẽ đổi K.

### 2.3.3 — Gom cụm và lập hồ sơ cụm

Chạy K-Means với K = 8, đánh số lại để cụm 1 lớn nhất. Bảng hồ sơ có hai cột kỹ năng: *đặc trưng* (lift cao, dùng để đặt tên) và *phổ biến nhất* (cho biết cụm "thường có gì", chưa chắc khác cụm khác). Nhóm nghề, cấp bậc, lương chỉ để mô tả, không tham gia gom cụm. Mỗi cụm có hai tin mẫu gần tâm nhất kèm đường dẫn để mở kiểm tra.

### 2.3.4 — Đặt tên cụm

Mỗi tên có một "chữ ký" là vài kỹ năng tiêu biểu. Cụm nhận tên có nhiều kỹ năng trùng chữ ký nhất (tối thiểu 2). Ô cuối kiểm tra mọi cụm có tên, không trùng tên và đủ 8 tên. Cách này giữ tên đúng khi chạy lại vì số thứ tự cụm có thể đổi nhưng kỹ năng đặc trưng thì không (đã kiểm ở 2.3.5).

### 2.3.5 — Kiểm tra độ tin cậy của cụm

**Chạy lại 20 hạt giống khác (mục mới).** K-Means khởi tạo ngẫu nhiên, và với dữ liệu 0/1 thưa này có nhiều lời giải gần như tốt ngang nhau. Đã thử tăng lên 1.000 lần khởi tạo nhưng các hạt giống vẫn cho cụm khác nhau, nên không "sửa" được bằng cách chạy nhiều hơn. Thay vào đó đo trực tiếp:

- *Tên cụm bền:* đủ 8 hồ sơ kỹ năng ở 20/20 lần chạy.
- *Ranh giới cụm thì không:* trung vị 96,3% tin giữ nguyên tên cụm so với lần chạy chính, thấp nhất 85,3%.
- *Dao động nhiều nhất* ở Data Science / ML / LLM (239–388 tin) và Dữ liệu doanh nghiệp (248–354 tin), nhiều khả năng vì Python và SQL có ở cả hai nên nhiều tin nằm giữa. Một lần chạy ở môi trường khác ra Data Science 405 và Dữ liệu doanh nghiệp 245, cùng kiểu dao động này.

**Vì sao K = 8 mà không phải 7?** Với K < 8 chắc chắn thiếu chỗ cho 8 hồ sơ, nên điều đáng xem là hồ sơ nào bị mất:

| K | Số lần chạy bị mất hồ sơ | Hồ sơ bị mất | Cụm Frontend và Web (trung vị) |
| -: | -: | --- | -: |
| 6 | 20/20 | Backend Java và Data Science (20 lần), Dữ liệu doanh nghiệp (2 lần) | 604 |
| 7 | 20/20 | Backend Java (19 lần), Data Science (1 lần) | 571 |
| 8 | 0/20 | không | 368 |

Ở K = 7, các tin Spring, Kafka, Redis (khoảng 330 tin) không còn cụm riêng và cụm Frontend phình từ khoảng 370 lên khoảng 570 tin. K = 8 là K nhỏ nhất giữ đủ 8 hồ sơ ở mọi hạt giống. Đây mới là lý do chọn K = 8, không phải Silhouette.

**Cụm nào chặt, cụm nào lẫn?** Silhouette từng cụm: chặt nhất là *C / C++ và Linux* (0,196) và *Agile / Scrum* (0,142); kém nhất là *Frontend và Web* (0,016) và *Data Science / ML / LLM* (0,030) vì JavaScript, React, Python có ở nhiều nhóm khác. Cả 8 cụm đều có Silhouette trung bình dương, nhưng 305/2.218 tin (13,8%) có điểm âm; riêng Frontend và Web có 140/363 tin âm (38,6%), trong đó 70 tin gần Backend Java nhất.

**Cụm có lệch theo nguồn dữ liệu không?** Có hai cụm lệch rõ so với toàn mẫu (TopCV 35%, LinkedIn 26%): *Hệ thống, mạng và bảo mật* (TopCV 57%, LinkedIn 3%) và *C / C++ và Linux* (LinkedIn 48%). Bước lọc kỹ năng cũng giữ lại mỗi nguồn khác nhau:

| Nguồn | Số tin có JD | Số tin vào cụm | % giữ lại |
| --- | ---: | ---: | ---: |
| TopCV | 1.138 | 776 | 68,2% |
| LinkedIn | 637 | 573 | 90,0% |
| ITviec | 530 | 458 | 86,4% |
| VietnamWorks | 477 | 360 | 75,5% |
| TopDev | 61 | 51 | 83,6% |
| **Toàn mẫu** | **2.843** | **2.218** | **78,0%** |

Vì vậy tỷ trọng của 8 cụm chỉ mô tả 2.218 tin có đủ kỹ năng trích xuất sau lọc, không mô tả cả 2.843 tin.

### 2.3.6 — Hình 2D (PCA)

Mỗi ô nhấn một cụm (màu xanh) trên nền toàn bộ tin (xám), nên không cần phân biệt 8 màu. PCA chỉ giữ khoảng 13% biến thiên nên hình chỉ để minh họa, không dùng để chọn K.

### 2.3.7 — Tổng kết mẫu số và lưu kết quả

Mọi tin IT có JD được ghi vào `data/cluster_assignments.csv` với một trạng thái: `clustered`, `no_skills_extracted` hoặc `too_few_skills`. Notebook đọc lại file và kiểm tra mỗi tin được tính đúng một lần (2.843 dòng).

## Câu hỏi có thể gặp khi vấn đáp

| Câu hỏi | Trả lời ngắn |
| ------- | ------------ |
| Vì sao K = 8? | K = 8 là K nhỏ nhất còn đủ 8 hồ sơ kỹ năng ở cả 20 hạt giống; K = 7 làm mất cụm Backend Java (19/20 lần). Silhouette của K = 6–8 chênh quá ít để làm căn cứ. |
| Quy tắc chọn K để làm gì nếu đã chốt K = 8? | Làm gợi ý và để kiểm tra: nếu nó gợi ý K khác, notebook in cảnh báo. Nó không tự đổi K nữa. |
| Chạy lại ở máy khác ra số khác thì có sai không? | Không sai. Tên cụm giữ nguyên, nhưng kích thước đổi và một phần tin đổi cụm (trung vị khoảng 4%, nhiều nhất khoảng 15% trong 20 hạt giống). Số liệu cho 2.4, 2.5 lấy từ `cluster_assignments.csv` đã lưu. |
| Elbow không có khuỷu thì sao? | Inertia giảm đều nên Elbow chỉ để quan sát; phải kết hợp Silhouette, độ ổn định và kiểm tra hồ sơ kỹ năng. |
| Silhouette thấp (0,074) có sao không? | Nhiều kỹ năng (Git, Docker, SQL) có ở mọi nhóm nên cụm chồng lấn. Kết quả là xu hướng kỹ năng, không phải ranh giới cứng giữa các nghề. |
| Vì sao phải chuẩn hóa vector? | Để cụm không bị quyết định bởi số lượng kỹ năng ghi trong tin. |
| Vì sao bỏ tin dưới 3 kỹ năng? | Tin ít kỹ năng gần như cách đều mọi tin khác, chỉ làm nhiễu khoảng cách. Chúng vẫn nằm trong file kết quả với trạng thái `too_few_skills`. |
| Lift là gì, vì sao không đặt tên bằng kỹ năng phổ biến nhất? | Lift = tỷ lệ kỹ năng trong cụm ÷ tỷ lệ trong toàn mẫu (lift 5 = nhắc nhiều gấp 5 lần bình thường). Python, SQL, Git phổ biến ở mọi cụm nên cụm nào cũng trông giống nhau; lift mới cho thấy điều làm cụm khác biệt. |

## Cách chạy lại

1. Mở `gom_cum.ipynb` trong thư mục `buoc 2.3`. Đường dẫn dữ liệu là tương đối: `../buoc2.1_2.2/data/processed/clean_data_processed.csv`.
2. Chạy `Restart Kernel → Run All`, mất khoảng 1–2 phút. `random_state = 42` ở mọi nơi.
3. Kết quả ghi vào `data/cluster_assignments.csv`. **Chạy lại sẽ ghi đè file này**; nếu chạy ở máy có phiên bản thư viện khác, kích thước cụm có thể lệch như mô tả ở 2.3.5 nên hãy giữ bản đã lưu (commit file) làm bản chốt.

> **Lưu ý:** Kết quả mô tả mẫu dữ liệu thu thập, chưa đại diện toàn bộ thị trường IT Việt Nam. Cụm dựa trên kỹ năng **được trích xuất** từ từ điển ở 2.1; kỹ năng bị bỏ sót sẽ không ảnh hưởng tới cụm. Lương chủ yếu từ TopCV với kỳ trả là giả định (xem 2.2), chỉ nên dùng để tham khảo. Nhóm nên kiểm lại kết quả 2.4, 2.5 theo từng nguồn vì có hai cụm lệch nguồn rõ. Nếu 2.5 dùng `cluster_name` để dự đoán cấp bậc hoặc lương thì phải kiểm tra rò rỉ dữ liệu.
