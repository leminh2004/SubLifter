import gradio as gr
import cv2
import os
import sys
from sublifter.core.ocr_engine import OCREngine
from sublifter.core.video_processor import VideoProcessor
from sublifter.core.sub_writer import write_srt, write_ass

def get_preview(video_path, ymin, ymax, xmin, xmax, scan_preset="Biên dưới (Mặc định - 20% dưới)"):
    """Generate a full frame with crop boundary overlay and a cropped preview."""
    if not video_path or not os.path.exists(video_path):
        return None, None
        
    cap = cv2.VideoCapture(video_path)
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        return None, None
        
    h, w, _ = frame.shape
    
    # Convert percentages to pixel values
    y_start = int(h * ymin)
    y_end = int(h * ymax)
    x_start = int(w * xmin)
    x_end = int(w * xmax)
    
    # Clip values just in case
    y_start, y_end = max(0, y_start), min(h, y_end)
    x_start, x_end = max(0, x_start), min(w, x_end)
    
    overlay_frame = frame.copy()
    
    # Get cropped region & Draw boundary box
    if scan_preset == "Cả trên và dưới (20% mỗi bên)":
        y_top_end = int(h * 0.2)
        y_bottom_start = int(h * 0.8)
        
        cv2.rectangle(overlay_frame, (x_start, 0), (x_end, y_top_end), (0, 0, 255), 3)
        cv2.rectangle(overlay_frame, (x_start, y_bottom_start), (x_end, h), (0, 0, 255), 3)
        
        top_crop = frame[0:y_top_end, x_start:x_end]
        bottom_crop = frame[y_bottom_start:h, x_start:x_end]
        if top_crop.size > 0 and bottom_crop.size > 0:
            import numpy as np
            cropped = np.vstack([top_crop, bottom_crop])
        else:
            cropped = frame[y_start:y_end, x_start:x_end]
    else:
        cv2.rectangle(overlay_frame, (x_start, y_start), (x_end, y_end), (0, 0, 255), 3)
        cropped = frame[y_start:y_end, x_start:x_end]
        
    # Convert to RGB for Gradio
    overlay_frame = cv2.cvtColor(overlay_frame, cv2.COLOR_BGR2RGB)
    
    if cropped.size > 0:
        cropped_rgb = cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB)
    else:
        cropped_rgb = None
        
    return overlay_frame, cropped_rgb

def extract_subtitles(video_path, scan_preset, lang_preset, sample_rate, ymin, ymax, xmin, xmax, diff_threshold, conf_threshold, out_format, preprocess_mode, width_ths, progress=gr.Progress()):
    if not video_path or not os.path.exists(video_path):
        return None, "Lỗi: Vui lòng tải lên hoặc chọn một tệp video hợp lệ."
        
    lang_map = {
        "Tiếng Việt + Tiếng Anh": ["vi", "en"],
        "Tiếng Nhật + Tiếng Anh": ["ja", "en"],
        "Tiếng Trung (Giản thể) + Tiếng Anh": ["ch_sim", "en"],
        "Tiếng Trung (Phồn thể) + Tiếng Anh": ["ch_tra", "en"],
        "Tiếng Hàn + Tiếng Anh": ["ko", "en"],
        "Chỉ Tiếng Anh": ["en"]
    }
    langs = lang_map.get(lang_preset, ["vi", "en"])
    if not langs:
        return None, "Lỗi: Ngôn ngữ không hợp lệ."
        
    try:
        progress(0, desc="Đang khởi tạo công cụ OCR...")
        ocr = OCREngine(languages=langs, confidence_threshold=conf_threshold)
        
        double_zone = (scan_preset == "Cả trên và dưới (20% mỗi bên)")
        
        processor = VideoProcessor(
            ocr_engine=ocr,
            sample_rate=sample_rate,
            ymin=ymin,
            ymax=ymax,
            xmin=xmin,
            xmax=xmax,
            diff_threshold=diff_threshold,
            preprocess_mode=preprocess_mode,
            double_zone=double_zone,
            width_ths=width_ths
        )
        
        def progress_callback(prog, status_text):
            progress(prog, desc=status_text)
            
        progress(0, desc="Đang xử lý các khung hình video...")
        subtitles = processor.process_video(video_path, progress_callback=progress_callback)
        
        # Save output subtitle file
        base, _ = os.path.splitext(video_path)
        output_path = f"{base}_extracted.{out_format}"
        
        if out_format == "srt":
            write_srt(subtitles, output_path)
        else:
            write_ass(subtitles, output_path)
            
        # Generate summary text
        summary = f"Đã trích xuất thành công {len(subtitles)} đoạn phụ đề.\nLưu tại: {output_path}\n\n--- Xem trước (50 dòng đầu tiên) ---\n"
        for idx, sub in enumerate(subtitles[:50], 1):
            summary += f"[{sub['start']:.2f}giây -> {sub['end']:.2f}giây] {sub['text']}\n"
        if len(subtitles) > 50:
            summary += f"\n... và {len(subtitles) - 50} đoạn khác."
            
        return output_path, summary
        
    except Exception as e:
        import traceback
        exc = traceback.format_exc()
        return None, f"Đã xảy ra lỗi:\n{e}\n\nChi tiết:\n{exc}"

def handle_preset(preset, ymin, ymax, xmin, xmax):
    if preset == "Biên dưới (Mặc định - 20% dưới)":
        return 0.80, 1.00, 0.00, 1.00, gr.update(visible=False)
    elif preset == "Biên trên (20% trên)":
        return 0.00, 0.20, 0.00, 1.00, gr.update(visible=False)
    elif preset == "Cả trên và dưới (20% mỗi bên)":
        return 0.80, 1.00, 0.00, 1.00, gr.update(visible=False)
    elif preset == "Toàn bộ màn hình (100%)":
        return 0.00, 1.00, 0.00, 1.00, gr.update(visible=False)
    else: # Tự chọn (Chỉnh tay)
        return ymin, ymax, xmin, xmax, gr.update(visible=True)

def build_gui():
    with gr.Blocks(title="SubLifter - Trích xuất phụ đề cứng") as demo:
        gr.Markdown(
            """
            # 🎬 SubLifter - Trích xuất phụ đề cứng
            Trích xuất phụ đề được ghi cứng (hardsub) từ tệp video và chuyển đổi thành tệp phụ đề `.srt` hoặc `.ass` có thể chỉnh sửa bằng EasyOCR.
            """
        )
        
        with gr.Row():
            with gr.Column(scale=1):
                video_input = gr.Video(label="Tải video lên", sources=["upload"])
                
                scan_preset = gr.Dropdown(
                    choices=[
                        "Biên dưới (Mặc định - 20% dưới)", 
                        "Biên trên (20% trên)", 
                        "Cả trên và dưới (20% mỗi bên)",
                        "Toàn bộ màn hình (100%)", 
                        "Tự chọn (Chỉnh tay)"
                    ],
                    value="Biên dưới (Mặc định - 20% dưới)",
                    label="Vùng quét phụ đề"
                )
                
                with gr.Group(visible=False) as manual_crop_group:
                    gr.Markdown("### 🔍 Cấu hình vùng chứa phụ đề (Tỷ lệ %)")
                    ymin = gr.Slider(0.0, 1.0, value=0.80, step=0.01, label="Y-Min (Biên trên)")
                    ymax = gr.Slider(0.0, 1.0, value=1.00, step=0.01, label="Y-Max (Biên dưới)")
                    xmin = gr.Slider(0.0, 1.0, value=0.00, step=0.01, label="X-Min (Biên trái)")
                    xmax = gr.Slider(0.0, 1.0, value=1.00, step=0.01, label="X-Max (Biên phải)")
                    
                out_format = gr.Radio(["srt", "ass"], value="srt", label="Định dạng phụ đề đầu ra")
                
                lang_preset = gr.Dropdown(
                    choices=[
                        "Tiếng Việt + Tiếng Anh",
                        "Tiếng Nhật + Tiếng Anh",
                        "Tiếng Trung (Giản thể) + Tiếng Anh",
                        "Tiếng Trung (Phồn thể) + Tiếng Anh",
                        "Tiếng Hàn + Tiếng Anh",
                        "Chỉ Tiếng Anh"
                    ],
                    value="Tiếng Việt + Tiếng Anh",
                    label="Ngôn ngữ nhận diện (OCR)",
                    info="Hỗ trợ ghép thêm tiếng Anh làm ngôn ngữ phụ để tối ưu chính tả."
                )
                
                with gr.Accordion("⚙️ Cấu hình nâng cao", open=False):
                    sample_rate = gr.Slider(0.5, 10.0, value=1.5, step=0.5, label="Tốc độ quét (Khung hình/giây)")
                    diff_thresh = gr.Slider(0.0, 10.0, value=2.0, step=0.5, label="Ngưỡng lệch khung hình (0 để quét toàn bộ)")
                    conf_thresh = gr.Slider(0.1, 0.9, value=0.35, step=0.05, label="Ngưỡng độ tin cậy OCR")
                    width_ths = gr.Slider(0.1, 1.0, value=0.5, step=0.05, label="Ngưỡng gộp chữ ngang (Width Threshold)", info="Giá trị mặc định là 0.5. Hạ xuống 0.2 - 0.3 nếu từ bị dính nhau. Tăng lên nếu từ bị rời rạc.")
                    preprocess_mode = gr.Dropdown(
                        choices=["none", "binarize", "adaptive", "color_mask"], 
                        value="none", 
                        label="Phương pháp tiền xử lý ảnh (Khử nhiễu nền)",
                        info="none: Giữ nguyên (Mặc định tối ưu cho hầu hết video) | binarize: Nhị phân hóa | adaptive: Tách viền (Chỉ dùng khi chữ có viền đen dày và nền cực sạch) | color_mask: Chỉ lấy màu trắng/vàng"
                    )
                    
                btn_run = gr.Button("🚀 Bắt đầu trích xuất phụ đề", variant="primary")
                
            with gr.Column(scale=1):
                gr.Markdown("### 🖼️ Xem trước khung hình")
                preview_image = gr.Image(label="Vùng quét giới hạn (Khung đỏ)", interactive=False)
                cropped_preview = gr.Image(label="Khung hình phụ đề được cắt", interactive=False)
                
                gr.Markdown("### 📄 Kết quả")
                output_file = gr.File(label="Tải tệp phụ đề về máy")
                output_text = gr.Textbox(label="Xem trước phụ đề / Nhật ký xử lý", lines=15, max_lines=25)
                
        # Interactive Preview Handlers
        preview_inputs = [video_input, ymin, ymax, xmin, xmax, scan_preset]
        preview_outputs = [preview_image, cropped_preview]
        
        # Update preview when video is uploaded or sliders change
        video_input.change(get_preview, inputs=preview_inputs, outputs=preview_outputs)
        ymin.change(get_preview, inputs=preview_inputs, outputs=preview_outputs)
        ymax.change(get_preview, inputs=preview_inputs, outputs=preview_outputs)
        xmin.change(get_preview, inputs=preview_inputs, outputs=preview_outputs)
        xmax.change(get_preview, inputs=preview_inputs, outputs=preview_outputs)
        
        # Change preset handler
        scan_preset.change(
            handle_preset,
            inputs=[scan_preset, ymin, ymax, xmin, xmax],
            outputs=[ymin, ymax, xmin, xmax, manual_crop_group]
        )
        # Also trigger preview update when preset dropdown changes
        scan_preset.change(get_preview, inputs=preview_inputs, outputs=preview_outputs)
        
        # Click Run
        btn_run.click(
            extract_subtitles,
            inputs=[video_input, scan_preset, lang_preset, sample_rate, ymin, ymax, xmin, xmax, diff_thresh, conf_thresh, out_format, preprocess_mode, width_ths],
            outputs=[output_file, output_text]
        )
        
    return demo

def main():
    demo = build_gui()
    # Launch locally
    demo.launch(inbrowser=True, share=False)

if __name__ == "__main__":
    main()
