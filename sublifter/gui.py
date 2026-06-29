import gradio as gr
import cv2
import os
import sys
from sublifter.core.ocr_engine import OCREngine
from sublifter.core.video_processor import VideoProcessor
from sublifter.core.sub_writer import write_srt, write_ass

def get_preview(video_path, ymin, ymax, xmin, xmax):
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
    
    # Draw boundary box
    overlay_frame = frame.copy()
    cv2.rectangle(overlay_frame, (x_start, y_start), (x_end, y_end), (0, 0, 255), 3)
    
    # Convert to RGB for Gradio
    overlay_frame = cv2.cvtColor(overlay_frame, cv2.COLOR_BGR2RGB)
    
    # Get cropped region
    cropped = frame[y_start:y_end, x_start:x_end]
    if cropped.size > 0:
        cropped_rgb = cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB)
    else:
        cropped_rgb = None
        
    return overlay_frame, cropped_rgb

def extract_subtitles(video_path, lang_str, sample_rate, ymin, ymax, xmin, xmax, diff_threshold, conf_threshold, out_format, preprocess_mode, progress=gr.Progress()):
    if not video_path or not os.path.exists(video_path):
        return None, "Lỗi: Vui lòng tải lên hoặc chọn một tệp video hợp lệ."
        
    langs = [lang.strip() for lang in lang_str.split(",") if lang.strip()]
    if not langs:
        return None, "Lỗi: Vui lòng nhập ít nhất một mã ngôn ngữ (ví dụ: vi)."
        
    try:
        progress(0, desc="Đang khởi tạo công cụ OCR...")
        ocr = OCREngine(languages=langs, confidence_threshold=conf_threshold)
        
        processor = VideoProcessor(
            ocr_engine=ocr,
            sample_rate=sample_rate,
            ymin=ymin,
            ymax=ymax,
            xmin=xmin,
            xmax=xmax,
            diff_threshold=diff_threshold,
            preprocess_mode=preprocess_mode
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
                
                with gr.Group():
                    gr.Markdown("### 🔍 Cấu hình vùng chứa phụ đề (Tỷ lệ %)")
                    ymin = gr.Slider(0.0, 1.0, value=0.80, step=0.01, label="Y-Min (Biên trên)")
                    ymax = gr.Slider(0.0, 1.0, value=1.00, step=0.01, label="Y-Max (Biên dưới)")
                    xmin = gr.Slider(0.0, 1.0, value=0.00, step=0.01, label="X-Min (Biên trái)")
                    xmax = gr.Slider(0.0, 1.0, value=1.00, step=0.01, label="X-Max (Biên phải)")
                    
                out_format = gr.Radio(["srt", "ass"], value="srt", label="Định dạng phụ đề đầu ra")
                
                with gr.Accordion("⚙️ Cấu hình nâng cao", open=False):
                    lang_input = gr.Textbox(value="vi,en", label="Ngôn ngữ OCR (phân tách bằng dấu phẩy)", placeholder="ví dụ: vi,en,ja")
                    sample_rate = gr.Slider(0.5, 10.0, value=2.0, step=0.5, label="Tốc độ quét (Khung hình/giây)")
                    diff_thresh = gr.Slider(0.0, 10.0, value=2.0, step=0.5, label="Ngưỡng lệch khung hình (0 để quét toàn bộ)")
                    conf_thresh = gr.Slider(0.1, 0.9, value=0.35, step=0.05, label="Ngưỡng độ tin cậy OCR")
                    preprocess_mode = gr.Dropdown(
                        choices=["none", "binarize", "adaptive", "color_mask"], 
                        value="none", 
                        label="Phương pháp tiền xử lý ảnh (Khử nhiễu nền)",
                        info="none: Giữ nguyên | binarize: Nhị phân hóa | adaptive: Tách viền (Khuyên dùng cho chữ có viền đen) | color_mask: Chỉ lấy màu trắng/vàng"
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
        preview_inputs = [video_input, ymin, ymax, xmin, xmax]
        preview_outputs = [preview_image, cropped_preview]
        
        # Update preview when video is uploaded or sliders change
        video_input.change(get_preview, inputs=preview_inputs, outputs=preview_outputs)
        ymin.change(get_preview, inputs=preview_inputs, outputs=preview_outputs)
        ymax.change(get_preview, inputs=preview_inputs, outputs=preview_outputs)
        xmin.change(get_preview, inputs=preview_inputs, outputs=preview_outputs)
        xmax.change(get_preview, inputs=preview_inputs, outputs=preview_outputs)
        
        # Click Run
        btn_run.click(
            extract_subtitles,
            inputs=[video_input, lang_input, sample_rate, ymin, ymax, xmin, xmax, diff_thresh, conf_thresh, out_format, preprocess_mode],
            outputs=[output_file, output_text]
        )
        
    return demo

def main():
    demo = build_gui()
    # Launch locally
    demo.launch(inbrowser=True, share=False)

if __name__ == "__main__":
    main()
