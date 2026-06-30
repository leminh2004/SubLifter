# Lịch sử Phiên bản Dự án SubLifter

Tài liệu này ghi lại toàn bộ lịch sử phiên bản của dự án phần mềm tách hardsub SubLifter, được sắp xếp theo thứ tự từ mới nhất đến cũ nhất.

---

## Tóm tắt chung
- **Tổng số phiên bản**: 7
- **Thời gian dự án**: Tháng 06/2026.

---

## Chi tiết các Phiên bản (Từ mới nhất đến cũ nhất)

### 0.1.6. Khắc phục lỗi khóa tệp video trên Windows & Chỉ dẫn cài đặt GPU CUDA
- **Ngày**: 30/06/2026
- **Chi tiết thay đổi**:
  - **Khắc phục lỗi khóa tệp video (Video not playable)**:
    * Bổ sung cơ chế đóng Generator chủ động (`generator.close()`) trong khối `finally` của hàm `extract_subtitles` tại `gui.py`.
    * Đảm bảo giải phóng tệp tin video ngay lập tức (gọi `cap.release()`) sau khi quét xong hoặc khi xảy ra ngoại lệ, giúp trình duyệt của Gradio luôn phát được video bình thường trên Windows.
  - **Cập nhật chỉ dẫn cài đặt tăng tốc GPU**:
    * Bổ sung chú thích lệnh cài đặt PyTorch GPU hỗ trợ CUDA 12.4 (`--index-url https://download.pytorch.org/whl/cu124`) và PaddlePaddle GPU trực tiếp lên đầu tệp `requirements.txt` để hỗ trợ thiết lập môi trường clone nhanh chóng.

---

### 0.1.5. Tích hợp song song PaddleOCR & Cơ chế Fallback tự động
- **Ngày**: 29/06/2026
- **Chi tiết thay đổi**:
  - **Tích hợp song song PaddleOCR**:
    * Thêm hỗ trợ công cụ nhận diện PaddleOCR mang lại độ chính xác tiếng Việt vượt trội và tốc độ xử lý trên GPU/CPU nhanh hơn đáng kể.
    * Ánh xạ tự động mã ngôn ngữ preset sang các mã ngôn ngữ tương ứng của PaddleOCR (`vi`, `japan`, `ch`, `chinese_cht`, `korean`, `en`).
  - **Cơ chế Fallback tự động an toàn**:
    * Viết lại `OCREngine` để tự động kiểm tra sự khả dụng của PaddleOCR trên máy người dùng.
    * Nếu chưa cài đặt thư viện hoặc thiếu driver GPU tương thích, hệ thống sẽ tự động chuyển hướng (fallback) sử dụng EasyOCR làm phương án dự phòng, tránh crash app.
  - **Cập nhật Giao diện & CLI**:
    * Bổ sung bộ chọn Engine OCR (`PaddleOCR` hoặc `EasyOCR`) trên cả giao diện Web GUI và tham số dòng lệnh CLI (`--engine`).
    * Thiết lập `PaddleOCR` làm engine mặc định.
  - **Cấu hình Thư viện**:
    * Thêm `paddleocr` và `paddlepaddle` vào `requirements.txt` để hỗ trợ cài đặt một lần cho tất cả.

---

### 0.1.4. Tối ưu hóa hiệu năng GPU (Adaptive Upscaling)
- **Ngày**: 29/06/2026
- **Chi tiết thay đổi**:
  - **Tối ưu hóa hiệu năng GPU (Adaptive Upscaling)**:
    * Thay thế việc phóng đại 2x cố định bằng cơ chế co giãn thích ứng: chỉ phóng to vùng ảnh khi chiều cao crop dưới 150px.
    * Giữ nguyên kích thước gốc đối với video độ phân giải cao (1080p/4K) giúp giải phóng băng thông tính toán và khôi phục tốc độ GPU siêu nhanh như ban đầu.
  - **Trực quan hóa tiến độ & Hiển thị phụ đề thời gian thực**:
    * Cho phép cập nhật danh sách phụ đề đã trích xuất và sửa lỗi trực quan trực tiếp lên màn hình **ngay lập tức theo thời gian thực** khi đang quét.
    * Tách biệt khu vực danh sách phụ đề mở rộng (`lines=17`) và hộp thoại **"Tiến độ công việc"** tối giản nằm ở cuối.
    * Định dạng hiển thị thời gian hoạt động và thời gian ước tính còn lại theo chuẩn `giờ:phút:giây` (`00:00:00`).
    * Ẩn hộp thoại tải tệp (`gr.File`) khi đang quét, chỉ hiện lại với chiều cao rút gọn (`height=70`) khi hoàn tất.
    * Loại bỏ hoàn toàn khung ảnh phụ đề được cắt nhỏ (`cropped_preview`) để tiết kiệm tối đa diện tích hiển thị chiều dọc.
  - **Tối ưu hóa thuật toán gộp phụ đề & Tần suất quét**:
    * Loại bỏ giới hạn chiều ngang (xmin=0.0, xmax=1.0) để đảm bảo không bị mất chữ ở hai biên của những dòng phụ đề dài.
    * Tăng tần suất quét (`sample_rate=4.0`) để giảm thiểu sai số lệch thời gian bắt đầu/kết thúc (sai số tối đa giảm xuống 250ms).
    * Cải tiến thuật toán `_clean_subtitles` thông minh hơn: hạ ngưỡng similarity xuống `0.70` (hoặc `0.60` nếu lấn thời gian) và thêm bộ so khớp chuỗi con (`is_substring`) để gộp hiệu quả phụ đề chạy chữ dần (typewriter) và karaoke, loại bỏ các dòng lặp/tách dòng không mong muốn.

---

### 0.1.3. Tối giản hóa giao diện, tích hợp bộ kiểm tra chính tả & cách từ (Spell Checker) bảo toàn Romaji và ETA
- **Ngày**: 29/06/2026
- **Chi tiết thay đổi**:
  - **Tối giản hóa giao diện người dùng & Cố định vùng quét tối ưu**:
    * Ẩn/xóa bỏ hoàn toàn khu vực cấu hình nâng cao (Advanced Settings), các thanh trượt và menu chọn vùng quét thủ công.
    * Cố định hoàn toàn khung check sub ngầm: **85% chiều ngang ở chính giữa** (xmin=0.075, xmax=0.925) và **40% chia đều ở 2 đầu chiều dọc** (Top 20% và Bottom 20% xếp chồng đứng).
    * Thiết lập tự động các thông số tối ưu ngầm (tốc độ quét `1.5`, độ tin cậy `0.35`, độ lệch `2.0`, `width_ths = 0.5`, chế độ lọc `none`).
    * Thêm checkbox bật/tắt bộ sửa lỗi chính tả trực quan.
  - **Tích hợp bộ tự động sửa lỗi chính tả & cách từ (Spell Checker & Auto-Spacing)**:
    * Sử dụng `pyspellchecker` và `wordsegment` để tự động phát hiện, tách các từ bị dính nhau (ví dụ: `Icareofus` -> `I care of us`) và sửa các từ tiếng Anh viết sai chính tả (ví dụ: `talec` -> `take`).
  - **Bảo toàn từ phiên âm Romaji tiếng Nhật**:
    * Thiết lập bộ lọc bảo toàn chữ Romaji thông minh thông qua quy luật cấu trúc âm tiết tiếng Nhật (Consonant-Vowel) và whitelist từ vựng Anime phổ biến (`Aqours`, `LoveLive`, `Chika`, `Saito Shuka`, `watashi`, `yume`,...).
    * Đảm bảo các từ Romaji này không bao giờ bị bộ sửa lỗi tiếng Anh nhận nhầm và sửa thành từ khác.
  - **Khắc phục lỗi trích xuất phụ đề tĩnh & Lọc nhiễu**:
    * Sửa lỗi mất câu khi video chuyển cảnh tĩnh bằng cơ chế kế thừa văn bản của khung hình trước (`prev_text`).
    * Điều chỉnh thuật toán gộp chỉ áp dụng cho phụ đề tĩnh có độ tương đồng cao (gap < 0.8s, similarity > 85%).
    * Lọc bỏ hoàn toàn các ký tự rác tồn tại trong duy nhất 1 khung hình (`M`, `27`, `t`, `0`).
  - **Tích hợp bộ ước tính thời gian hoàn thành (ETA)**:
    * Tự động đo lường thời gian xử lý thực tế và tỷ lệ tiến trình để tính toán thời gian còn lại (định dạng `MM:SS`) và cập nhật liên tục lên thanh trạng thái xử lý của giao diện Web giúp người dùng dễ dàng theo dõi.

---

### 0.1.2. Khắc phục lỗi dính liền chữ (width_ths), tối ưu cấu hình mặc định và giám sát GPU
- **Ngày**: 29/06/2026
- **Chi tiết thay đổi**:
  - **Khắc phục lỗi dính liền chữ (thiếu khoảng trắng)**:
    * Thêm cấu hình tham số `width_ths` (Ngưỡng gộp từ ngang) của EasyOCR trên cả giao diện Web và dòng lệnh CLI.
    * Cho phép người dùng linh hoạt điều chỉnh (hạ xuống `0.2` - `0.3`) để tách rời các từ bị dính liền dấu cách do khoảng cách ký tự hẹp.
  - **Cấu hình tối ưu mặc định (Default Settings)**:
    * Đặt giá trị mặc định cho tốc độ quét là `1.5` khung hình/giây (quét mỗi 0.67s) giúp tối ưu thời gian xử lý và độ chính xác của phụ đề.
    * Đặt mặc định bộ lọc tiền xử lý khử nhiễu về `none` (Giữ nguyên) để tránh tạo ra nhiễu hạt gây nhận diện sai từ nền video phức tạp.
    * Đặt mặc định ngưỡng gộp từ ngang `width_ths` về lại `0.5` để đảm bảo nhận diện từ tiếng Anh toàn vẹn, tránh bị tách nhỏ từ.
  - **Nâng cấp giám sát hoạt động của Card đồ họa (GPU)**:
    * Tự động kiểm tra tính khả dụng của CUDA (`torch.cuda.is_available()`) khi khởi chạy OCR và truyền tường minh cờ `gpu=use_gpu` vào EasyOCR, đồng thời in thông báo xác thực GPU đang chạy lên terminal.

---

### 0.1.1. Bổ sung bộ chọn ngôn ngữ lập sẵn, ẩn hiện vùng quét nâng cao và hoàn thiện giao diện
- **Ngày**: 29/06/2026
- **Chi tiết thay đổi**:
  - **Cải tiến lựa chọn ngôn ngữ (OCR)**:
    * Thay thế hộp thoại nhập mã ngôn ngữ tự do bằng menu thả xuống chọn nhanh (Việt+Anh, Nhật+Anh, Trung+Anh, Hàn+Anh, chỉ Anh) giúp bổ trợ tự động từ điển chính tả tiếng Anh khi nhận diện.
  - **Tối ưu hóa bộ lọc vùng quét phụ đề**:
    * Ẩn các thanh trượt tọa độ crop mặc định và thay thế bằng menu thả xuống chọn vùng quét (Biên dưới, Biên trên, Cả trên và dưới, Toàn màn hình, Tự chọn).
    * Hỗ trợ chế độ "Cả trên và dưới (20% mỗi bên)" bằng cách vẽ đồng thời hai khung đỏ và xếp chồng hai vùng crop theo chiều dọc để OCR một lần cực kỳ nhanh.
    * Sử dụng cơ chế phản hồi động của Gradio để tự động ẩn/hiển thị nhóm thanh trượt thủ công chỉ khi chọn chế độ "Tự chọn (Chỉnh tay)".

---

### 0.1.0. Khởi tạo dự án SubLifter, tích hợp công cụ trích xuất phụ đề cứng (EasyOCR + OpenCV) hỗ trợ GPU và giao diện Web (Gradio)
- **Ngày**: 29/06/2026
- **Chi tiết thay đổi**:
  - **Khởi tạo cấu trúc dự án & thiết lập môi trường**:
    * Cài đặt môi trường ảo `.venv`, tạo tệp cấu hình [.gitignore](file:///d:/Projects/BanG%20Dream!/11.%20Project/SubLifter/.gitignore) và [requirements.txt](file:///d:/Projects/BanG%20Dream!/11.%20Project/SubLifter/requirements.txt) quản lý các thư viện (OpenCV, EasyOCR, Gradio, NumPy, tqdm).
  - **Tích hợp tăng tốc GPU (CUDA 12.1)**:
    * Cấu hình và cài đặt phiên bản PyTorch hỗ trợ GPU CUDA (`torch-2.5.1+cu121` và `torchvision-0.20.1+cu121`) giúp tăng tốc độ nhận diện phụ đề gấp 10-20 lần sử dụng card đồ họa NVIDIA GeForce GTX 1650.
  - **Phát triển lõi xử lý phụ đề (Core)**:
    * [sub_writer.py](file:///d:/Projects/BanG%20Dream!/11.%20Project/SubLifter/sublifter/core/sub_writer.py): Xử lý chuyển đổi thời gian sang định dạng chuẩn phụ đề và ghi tệp `.srt` / `.ass`. Khắc phục lỗi unicode escape đối với ký tự xuống dòng `\N` của tệp ASS.
    * [ocr_engine.py](file:///d:/Projects/BanG%20Dream!/11.%20Project/SubLifter/sublifter/core/ocr_engine.py): Tiền xử lý lọc nhiễu ảnh nâng cao (nhị phân hóa Otsu, ngưỡng thích ứng Gaussian tách viền chữ đen nền trắng - `adaptive`, lọc dải màu HSV Trắng/Vàng - `color_mask`). Nhận diện văn bản bằng EasyOCR và gộp nhóm dòng chữ dựa trên tọa độ trục Y.
    * [video_processor.py](file:///d:/Projects/BanG%20Dream!/11.%20Project/SubLifter/sublifter/core/video_processor.py): Thực hiện lấy mẫu khung hình theo tần suất (sample rate) và so sánh độ lệch pixel tại vùng crop để bỏ qua các khung hình tĩnh trùng lặp, tối ưu tài nguyên phần cứng.
  - **Xây dựng Giao diện điều khiển (CLI & Web UI)**:
    * [gui.py](file:///d:/Projects/BanG%20Dream!/11.%20Project/SubLifter/sublifter/gui.py): Thiết kế giao diện Web Việt hóa trực quan chạy cục bộ bằng Gradio. Đặt thanh tùy chọn xuất định dạng `.srt`/`.ass` trực tiếp ở giao diện chính để dễ thao tác.
    * [cli.py](file:///d:/Projects/BanG%20Dream!/11.%20Project/SubLifter/sublifter/cli.py): Xây dựng giao diện dòng lệnh bằng tiếng Việt tích hợp thanh tiến trình `tqdm` chuyên nghiệp.
  - **Xây dựng Script kiểm thử tự động**:
    * [test_pipeline.py](file:///d:/Projects/BanG%20Dream!/11.%20Project/SubLifter/tests/test_pipeline.py): Tạo kịch bản tự tạo video giả lập chứa chữ và chạy kiểm tra toàn bộ luồng trích xuất, ghi nhận kết quả và dọn dẹp bộ nhớ tạm tự động.
