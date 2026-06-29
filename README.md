# SubLifter - Trình trích xuất phụ đề cứng (Hardsub Extractor)

SubLifter là một công cụ Python được thiết kế để trích xuất phụ đề được ghi cứng (hardsub) từ các tệp video và chuyển đổi chúng thành các định dạng phụ đề tiêu chuẩn (`.srt` hoặc `.ass`). Hệ thống sử dụng **OpenCV** để xử lý video và **EasyOCR** (chạy trên nền PyTorch) để nhận diện văn bản.

## Các tính năng nổi bật

- **Hỗ trợ đa ngôn ngữ**: Nhận diện tốt tiếng Việt, tiếng Anh, tiếng Nhật và hơn 80 ngôn ngữ khác được hỗ trợ bởi EasyOCR.
- **Giao diện Web trực quan (Gradio)**: Kéo thả điều chỉnh và xem trước vùng quét phụ đề thời gian thực bằng các thanh trượt tỷ lệ và khung hiển thị màu đỏ trực quan.
- **Tăng tốc phần cứng GPU**: Hỗ trợ tăng tốc nhận diện phụ đề gấp 10-20 lần bằng Card đồ họa NVIDIA (thông qua thư viện CUDA).
- **Bộ lọc khử nhiễu ảnh nâng cao**: Hỗ trợ nhị phân hóa cục bộ, tách viền chữ đen nền trắng (Adaptive Thresholding) và lọc dải màu HSV (Trắng/Vàng) để loại bỏ hoàn toàn nền video phức tạp.
- **Quét khung hình thông minh**: Tự động so sánh độ lệch pixel để bỏ qua các khung hình tĩnh trùng lặp, tăng tốc độ xử lý của CPU/GPU.
- **Tự động ghép từ**: Tự động liên kết và sửa các lỗi chính tả hoặc lệch ký tự nhỏ giữa các khung hình liên tiếp của cùng một câu phụ đề.
- **Định dạng xuất**: Hỗ trợ lưu trữ phụ đề dưới dạng tệp `.srt` hoặc `.ass`.

---

## Hướng dẫn Cài đặt

1. Tạo môi trường ảo và kích hoạt nó:
   ```bash
   # Windows PowerShell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   
   # Linux/macOS
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Cài đặt các thư viện phụ thuộc:
   ```bash
   pip install -r requirements.txt
   ```
   
   *Lưu ý: Để kích hoạt tăng tốc GPU (CUDA), hãy chạy lệnh cài đặt PyTorch GPU chuyên dụng:*
   ```bash
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121 --force-reinstall
   ```

---

## Hướng dẫn Khởi chạy

### Cách 1: Sử dụng Giao diện Web (Khuyên dùng)

Để mở giao diện điều khiển trên trình duyệt web, chạy lệnh sau:

```bash
# Windows
.venv\Scripts\python.exe -m sublifter.gui

# Linux/macOS
.venv/bin/python -m sublifter.gui
```

Ứng dụng sẽ khởi động một máy chủ cục bộ và tự động mở một trang web trong trình duyệt mặc định của bạn (thường tại địa chỉ `http://127.0.0.1:7860`).

**Các bước sử dụng:**
1. **Tải video lên** ở khung bên trái.
2. Điều chỉnh thanh trượt **Cấu hình vùng chứa phụ đề**. Một khung màu đỏ sẽ bao quanh vùng quét trên ảnh xem trước toàn cảnh, và vùng phụ đề được cắt phóng to sẽ hiển thị ngay bên cạnh.
3. Chọn định dạng phụ đề xuất ra mong muốn (`.srt` hoặc `.ass`) ngay ở màn hình chính.
4. Điều chỉnh thêm các tham số như ngôn ngữ quét (ví dụ: `vi,en`), tốc độ quét, phương pháp tiền xử lý khử nhiễu (khuyên dùng chế độ `adaptive` cho chữ có viền đen) trong hộp thoại **⚙️ Cấu hình nâng cao**.
5. Bấm nút **🚀 Bắt đầu trích xuất phụ đề** để chạy và tải tệp phụ đề về máy.

---

### Cách 2: Sử dụng Dòng lệnh (CLI)

Để tiến hành trích xuất phụ đề nhanh trực tiếp trong cửa sổ terminal, chạy lệnh:

```bash
.venv\Scripts\python.exe -m sublifter.cli -i "duong_dan_video.mp4" -o "phu_de_dau_ra.srt" -l "vi,en" --ymin 0.8 --ymax 1.0 --preprocess adaptive
```

#### Các tham số dòng lệnh:
* `-i`, `--input` (Bắt buộc): Đường dẫn tới tệp video đầu vào.
* `-o`, `--output` (Tùy chọn): Đường dẫn lưu tệp phụ đề (mặc định lưu cùng thư mục với video).
* `-f`, `--format` (Tùy chọn): Định dạng phụ đề đầu ra, chọn `srt` hoặc `ass` (mặc định: `srt`).
* `-l`, `--languages` (Tùy chọn): Các mã ngôn ngữ OCR phân tách bằng dấu phẩy, ví dụ `vi,en,ja` (mặc định: `vi,en`).
* `--sample-rate` (Tùy chọn): Tốc độ quét (số khung hình xử lý mỗi giây). Số càng lớn quét càng mịn nhưng càng chậm (mặc định: `2.0`).
* `--ymin`, `--ymax`, `--xmin`, `--xmax` (Tùy chọn): Tỷ lệ tọa độ cắt từ `0.0` đến `1.0` để định vị phụ đề (mặc định quét 20% bên dưới: `--ymin 0.8 --ymax 1.0 --xmin 0.0 --xmax 1.0`).
* `--diff-threshold` (Tùy chọn): Ngưỡng lệch pixel để nhận diện đổi câu. Nhập `0` để ép phần mềm quét OCR trên mọi khung hình mẫu (mặc định: `2.0`).
* `--preprocess` (Tùy chọn): Phương pháp tiền xử lý ảnh khử nhiễu: `none` (mặc định), `binarize` (nhị phân), `adaptive` (ngưỡng thích ứng tách viền), `color_mask` (lọc màu Trắng/Vàng).
* `-c`, `--conf` (Tùy chọn): Ngưỡng độ tin cậy của chữ nhận diện được từ `0.0` đến `1.0` (mặc định: `0.35`).
