# Lịch sử Phiên bản Dự án SubLifter

Tài liệu này ghi lại toàn bộ lịch sử phiên bản của dự án phần mềm tách hardsub SubLifter, được sắp xếp theo thứ tự từ mới nhất đến cũ nhất.

---

## Tóm tắt chung
- **Tổng số phiên bản**: 2
- **Thời gian dự án**: Tháng 06/2026.

---

## Chi tiết các Phiên bản (Từ mới nhất đến cũ nhất)

### 0.1.1. Bổ sung bộ chọn ngôn ngữ lập sẵn, ẩn hiện vùng quét nâng cao và hoàn thiện giao diện
- **Ngày**: 29/06/2026
- **Chi tiết thay đổi**:
  - **Cải tiến lựa chọn ngôn ngữ (OCR)**:
    * Thay thế hộp thoại nhập mã ngôn ngữ tự do bằng menu thả xuống chọn nhanh (Việt+Anh, Nhật+Anh, Trung+Anh, Hàn+Anh, chỉ Anh) giúp bổ trợ tự động từ điển chính tả tiếng Anh khi nhận diện.
  - **Tối ưu hóa bộ lọc vùng quét phụ đề**:
    * Ẩn các thanh trượt tọa độ crop mặc định và thay thế bằng menu thả xuống chọn vùng quét (Biên dưới, Biên trên, Cả trên và dưới, Toàn màn hình, Tự chọn).
    * Hỗ trợ chế độ "Cả trên và dưới (20% mỗi bên)" bằng cách vẽ đồng thời hai khung đỏ và xếp chồng hai vùng crop theo chiều dọc để OCR một lần cực kỳ nhanh.
    * Sử dụng cơ chế phản hồi động của Gradio để tự động ẩn/hiển thị nhóm thanh trượt thủ công chỉ khi chọn chế độ "Tự chọn (Chỉnh tay)".
  - **Khắc phục lỗi dính liền chữ (thiếu khoảng trắng)**:
    * Thêm cấu hình tham số `width_ths` (Ngưỡng gộp từ ngang) của EasyOCR trên cả giao diện Web và dòng lệnh CLI.
    * Cho phép người dùng hạ thấp ngưỡng này xuống `0.2` - `0.3` để tách rời các từ bị dính liền dấu cách do khoảng cách ký tự hẹp.
  - **Cấu hình tối ưu hóa mặc định (Default Settings) & Giám sát GPU**:
    * Đặt giá trị mặc định cho tốc độ quét là `1.5` khung hình/giây (quét mỗi 0.67s) giúp tối ưu thời gian xử lý và độ chính xác của phụ đề.
    * Thiết lập mặc định bộ lọc tiền xử lý khử nhiễu là `adaptive` (Gaussian) để tối ưu nhất cho kiểu hardsub có viền đen chữ trắng/gradient.
    * Thiết lập mặc định ngưỡng gộp từ ngang `width_ths` là `0.3` để tự động chống dính chữ.
    * Nâng cấp ghi nhật ký khi khởi tạo EasyOCR, tự động kiểm tra `torch.cuda.is_available()` và truyền tường minh cờ `gpu=use_gpu` đồng thời in thông báo xác thực GPU hoạt động lên terminal.

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
