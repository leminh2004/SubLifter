# SubLifter - Trình trích xuất phụ đề cứng (Hardsub Extractor)

SubLifter là một công cụ Python được thiết kế để trích xuất phụ đề được ghi cứng (hardsub) từ các tệp video và chuyển đổi chúng thành các định dạng phụ đề tiêu chuẩn (`.srt` hoặc `.ass`). Hệ thống sử dụng **OpenCV** để xử lý video và **EasyOCR** (chạy trên nền PyTorch) để nhận diện văn bản.

---

## Các tính năng nổi bật

- **Tối giản hóa giao diện**: Giao diện trực quan, lược bỏ hoàn toàn các thanh trượt phức tạp để tạo cấu hình tối ưu sẵn có ngầm (tốc độ quét `1.5` hình/giây, độ tin cậy `0.35`, độ lệch `2.0`, `width_ths = 0.5`, chế độ tiền xử lý `none`).
- **Khung quét phụ đề cố định (Optimal Crop Box)**: Cố định ngầm khung check phụ đề tối ưu nhất cho hardsub: **85% chiều ngang ở chính giữa** (để tránh rác biên) và **40% chia đều ở 2 đầu chiều dọc** (Top 20% và Bottom 20% xếp chồng đứng để nhận diện đồng thời cả sub trên và dưới cực nhanh).
- **Bộ tự động sửa lỗi chính tả & cách từ (Spell Checker & Auto-Spacing)**: Chạy thời gian thực song song với tiến trình quét. Tự động tách các từ bị dính liền do khoảng cách ký tự hẹp (ví dụ: `Icareofus` -> `I care of us`) và sửa lỗi chính tả tiếng Anh (ví dụ: `talec` -> `take`).
- **Bảo toàn từ phiên âm Romaji tiếng Nhật**: Tích hợp bộ lọc nhận dạng cấu trúc âm tiết tiếng Nhật (Consonant-Vowel) và whitelist từ vựng Anime phổ biến (`Aqours`, `LoveLive`, `watashi`, `yume`, tên nhân vật...). Đảm bảo các từ này không bị bộ sửa lỗi tiếng Anh nhận nhầm và sửa sai.
- **Tăng tốc phần cứng GPU**: Hỗ trợ tăng tốc nhận diện phụ đề gấp 10-20 lần bằng Card đồ họa NVIDIA (thông qua thư viện CUDA).
- **Khắc phục lỗi trích xuất phụ đề tĩnh**: Tự động kế thừa văn bản của khung hình trước (`prev_text`) khi bỏ qua khung hình tĩnh, ngăn chặn triệt để hiện tượng mất chữ hoặc nhấp nháy phụ đề.
- **Lọc nhiễu hạt đơn khung hình**: Tự động phát hiện và loại bỏ các ký tự rác hoặc số ngẫu nhiên chỉ tồn tại trong 1 khung hình quét (như `M`, `27`, `t`, `0`).
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
   
   *Lưu ý: Để kích hoạt tăng tốc GPU (CUDA) giúp trích xuất siêu tốc, hãy chạy lệnh cài đặt PyTorch GPU chuyên dụng:*
   ```bash
   # Dành cho CUDA 12.1 / 12.4
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124 --force-reinstall
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

Ứng dụng sẽ khởi động một máy chủ cục bộ và tự động mở một trang web trong trình duyệt mặc định của bạn (thường tại địa chỉ `http://127.0.0.1:7860` hoặc `7862`).

**Các bước sử dụng:**
1. **Tải video lên** ở khung bên trái.
2. Kiểm tra **Ảnh xem trước** ở khung bên phải: Hai khung màu đỏ thể hiện chính xác 2 vùng quét cố định (Biên trên 20% và Biên dưới 20%, chiều ngang thụt lề 7.5% mỗi bên). Ảnh phụ đề xếp chồng cũng sẽ được hiển thị ngay bên dưới để bạn quan sát.
3. Chọn định dạng phụ đề xuất ra mong muốn (`.srt` hoặc `.ass`).
4. Chọn **Ngôn ngữ nhận diện** (ví dụ: `Tiếng Việt + Tiếng Anh` hoặc `Tiếng Nhật + Tiếng Anh`).
5. Tùy chọn bật/tắt **Tự động sửa lỗi chính tả & cách từ (Spell Checker)**. Mặc định tính năng này luôn bật.
6. Bấm nút **🚀 Bắt đầu trích xuất phụ đề** để chạy, xem nhật ký log trực quan và tải tệp phụ đề về máy.

---

### Cách 2: Sử dụng Dòng lệnh (CLI)

Để tiến hành trích xuất phụ đề nhanh trực tiếp trong cửa sổ terminal, chạy lệnh:

```bash
.venv\Scripts\python.exe -m sublifter.cli -i "duong_dan_video.mp4" -o "phu_de_dau_ra.srt" -l "vi,en"
```

#### Các tham số dòng lệnh:
* `-i`, `--input` (Bắt buộc): Đường dẫn tới tệp video đầu vào.
* `-o`, `--output` (Tùy chọn): Đường dẫn lưu tệp phụ đề (mặc định lưu cùng thư mục với video).
* `-f`, `--format` (Tùy chọn): Định dạng phụ đề đầu ra, chọn `srt` hoặc `ass` (mặc định: `srt`).
* `-l`, `--languages` (Tùy chọn): Các mã ngôn ngữ OCR phân tách bằng dấu phẩy, ví dụ `vi,en,ja` (mặc định: `vi,en`).
* `--no-spellcheck` (Tùy chọn): Tắt tính năng tự động sửa lỗi chính tả và cách từ.
* `--sample-rate` (Tùy chọn): Tốc độ quét (số khung hình xử lý mỗi giây, mặc định: `1.5`).
* `--ymin`, `--ymax`, `--xmin`, `--xmax` (Tùy chọn): Tọa độ cắt thủ công từ `0.0` đến `1.0` (mặc định quét 2 vùng: top 20% và bottom 20%, ngang 85% ở giữa).
* `--diff-threshold` (Tùy chọn): Ngưỡng lệch pixel để nhận diện đổi câu (mặc định: `2.0`).
* `--preprocess` (Tùy chọn): Phương pháp tiền xử lý ảnh khử nhiễu: `none` (mặc định), `binarize`, `adaptive`, `color_mask`.
* `-c`, `--conf` (Tùy chọn): Ngưỡng độ tin cậy của chữ nhận diện được từ `0.0` đến `1.0` (mặc định: `0.35`).
