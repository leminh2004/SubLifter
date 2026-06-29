import gradio as gr
import cv2
import os
import sys
import numpy as np
import time
from sublifter.core.ocr_engine import OCREngine
from sublifter.core.video_processor import VideoProcessor
from sublifter.core.sub_writer import write_srt, write_ass

def format_time(seconds):
    """Format seconds into HH:MM:SS string."""
    if seconds is None or seconds < 0:
        return "00:00:00"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def make_progress_html(percent, elapsed, eta):
    """Generate custom premium progress bar HTML with times in HH:MM:SS."""
    percent_val = int(percent * 100)
    elapsed_str = format_time(elapsed)
    eta_str = format_time(eta)
    
    html = f"""
    <div style='border: 1px solid #ddd; padding: 10px; border-radius: 5px; background-color: #f9f9f9; font-family: sans-serif; height: auto;'>
        <p style='margin: 0; font-size: 14px; font-weight: bold; color: #333;'>Tiến độ công việc: {percent_val}%</p>
        <div style='background-color: #eee; border-radius: 4px; height: 12px; margin: 8px 0; overflow: hidden;'>
            <div style='background: linear-gradient(90deg, #4b6cb7 0%, #182848 100%); width: {percent_val}%; height: 100%; transition: width 0.2s ease;'></div>
        </div>
        <div style='display: flex; justify-content: space-between; font-size: 12px; color: #555;'>
            <span>Thời gian đã hoạt động: <b>{elapsed_str}</b></span>
            <span>Thời gian còn lại: <b>{eta_str}</b></span>
        </div>
    </div>
    """
    return html

def get_preview(video_path):
    """Generate a full frame with crop boundary overlay (full width horizontal, top+bottom 20% vertical)."""
    if not video_path or not os.path.exists(video_path):
        return None
        
    cap = cv2.VideoCapture(video_path)
    try:
        ret, frame = cap.read()
        if not ret:
            return None
            
        h, w, _ = frame.shape
        
        # Fixed Coordinates:
        # Horizontal: Full width
        # Vertical: Top 20% (0.0 to 0.2) & Bottom 20% (0.8 to 1.0)
        x_start = 0
        x_end = w
        y_top_end = int(h * 0.2)
        y_bottom_start = int(h * 0.8)
        
        overlay_frame = frame.copy()
        
        # Draw two red boxes for visual crop preview (full width)
        cv2.rectangle(overlay_frame, (x_start, 0), (x_end, y_top_end), (0, 0, 255), 3)
        cv2.rectangle(overlay_frame, (x_start, y_bottom_start), (x_end, h), (0, 0, 255), 3)
        
        # Convert to RGB for Gradio
        overlay_frame = cv2.cvtColor(overlay_frame, cv2.COLOR_BGR2RGB)
        
        return overlay_frame
    finally:
        cap.release()

def extract_subtitles(video_path, ocr_engine_name, lang_preset, out_format, use_spellcheck):
    if not video_path or not os.path.exists(video_path):
        yield None, "Lỗi: Vui lòng tải lên hoặc chọn một tệp video hợp lệ.", make_progress_html(0.0, 0.0, 0.0)
        return
        
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
        yield None, "Lỗi: Ngôn ngữ không hợp lệ.", make_progress_html(0.0, 0.0, 0.0)
        return
        
    engine_type = "paddle" if "PaddleOCR" in ocr_engine_name else "easyocr"
    try:
        # Initialize ocr
        ocr = OCREngine(languages=langs, confidence_threshold=0.35, engine_type=engine_type)
        
        # Fixed optimal settings under the hood
        processor = VideoProcessor(
            ocr_engine=ocr,
            sample_rate=4.0,  # Increased sample_rate to 4.0 for higher timing accuracy (250ms intervals)
            ymin=0.8,
            ymax=1.0,
            xmin=0.0,         # Full width
            xmax=1.0,         # Full width
            diff_threshold=2.0,
            preprocess_mode='none',
            double_zone=True,
            width_ths=0.5,
            use_spellcheck=use_spellcheck,
            lang_preset=lang_preset
        )
        
        # Start generator
        generator = processor.process_video_yield(video_path)
        
        for progress, elapsed, eta, current_subs in generator:
            # Build real-time subtitle preview text
            subs_text = ""
            for idx, sub in enumerate(current_subs, 1):
                subs_text += f"[{format_time(sub['start'])} -> {format_time(sub['end'])}] {sub['text']}\n"
            
            # Yield progress and real-time subtitles
            yield gr.update(visible=False), subs_text, make_progress_html(progress, elapsed, eta)
            
        # Final result (after generator finished, the last item has cleaned_subtitles)
        base, _ = os.path.splitext(video_path)
        output_path = f"{base}_extracted.{out_format}"
        
        if out_format == "srt":
            write_srt(current_subs, output_path)
        else:
            write_ass(current_subs, output_path)
            
        # Build final final text
        final_summary = f"Đã trích xuất thành công {len(current_subs)} đoạn phụ đề.\nLưu tại: {output_path}\n\n--- Danh sách phụ đề ---\n"
        for idx, sub in enumerate(current_subs, 1):
            final_summary += f"[{format_time(sub['start'])} -> {format_time(sub['end'])}] {sub['text']}\n"
            
        yield gr.update(visible=True, value=output_path), final_summary, make_progress_html(1.0, elapsed, 0.0)
        
    except Exception as e:
        import traceback
        exc = traceback.format_exc()
        yield gr.update(visible=False), f"Đã xảy ra lỗi:\n{e}\n\nChi tiết:\n{exc}", make_progress_html(0.0, 0.0, 0.0)

def build_gui():
    with gr.Blocks(title="SubLifter - Trích xuất phụ đề cứng") as demo:
        gr.Markdown(
            """
            #🎬 SubLifter - Trích xuất phụ đề cứng
            Trích xuất phụ đề được ghi cứng (hardsub) từ tệp video và chuyển đổi thành tệp phụ đề `.srt` hoặc `.ass` có thể chỉnh sửa bằng PaddleOCR hoặc EasyOCR.
            """
        )
        
        with gr.Row():
            with gr.Column(scale=1):
                video_input = gr.Video(label="Tải video lên", sources=["upload"])
                out_format = gr.Radio(["srt", "ass"], value="srt", label="Định dạng phụ đề đầu ra")
                
                ocr_engine_name = gr.Radio(
                    ["PaddleOCR (Khuyên dùng)", "EasyOCR"],
                    value="PaddleOCR (Khuyên dùng)",
                    label="Công cụ OCR (Engine)",
                    info="PaddleOCR cho độ chính xác tiếng Việt vượt trội và tốc độ cao. EasyOCR dùng làm dự phòng."
                )
                
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
                
                use_spellcheck = gr.Checkbox(
                    value=True,
                    label="Tự động sửa lỗi chính tả & cách từ (Spell Checker)",
                    info="Tự động sửa lỗi dính chữ tiếng Anh, sửa lỗi chính tả và bảo toàn từ Romaji tiếng Nhật."
                )
                    
                btn_run = gr.Button("🚀 Bắt đầu trích xuất phụ đề", variant="primary")
                
            with gr.Column(scale=1):
                gr.Markdown("### 🖼️ Xem trước khung hình")
                gr.Markdown("Khung check phụ đề được cố định: **85% chiều ngang (ở giữa)** và **40% chia đều ở 2 đầu chiều dọc** (Top 20% & Bottom 20%).")
                preview_image = gr.Image(label="Vùng quét giới hạn (Khung đỏ)", interactive=False)
                
                gr.Markdown("### 📄 Kết quả")
                output_file = gr.File(label="Tải tệp phụ đề về máy", visible=False, height=70)
                
                # Box 2: Phụ đề đã trích xuất & tự động sửa (height expanded)
                preview_subs_box = gr.Textbox(
                    label="Phụ đề đã trích xuất & tự động sửa", 
                    value="", 
                    lines=17, 
                    max_lines=28,
                    interactive=False,
                    autoscroll=False
                )
                
                # Box 1: Tiến độ công việc (height shrunken to fit progress info)
                progress_html = gr.HTML(
                    value="""
                    <div style='border: 1px solid #ddd; padding: 10px; border-radius: 5px; background-color: #f9f9f9; font-family: sans-serif;'>
                        <p style='margin: 0; font-size: 14px; font-weight: bold; color: #555;'>Tiến độ công việc</p>
                        <div style='background-color: #eee; border-radius: 4px; height: 12px; margin: 8px 0; overflow: hidden;'>
                            <div style='background-color: #4b6cb7; width: 0%; height: 100%;'></div>
                        </div>
                        <div style='display: flex; justify-content: space-between; font-size: 12px; color: #666;'>
                            <span>Thời gian đã hoạt động: 00:00:00</span>
                            <span>Thời gian còn lại: 00:00:00</span>
                        </div>
                    </div>
                    """,
                    label="Tiến độ công việc"
                )
                
        # Update preview when video is uploaded
        video_input.change(get_preview, inputs=[video_input], outputs=[preview_image])
        
        # Click Run
        btn_run.click(
            extract_subtitles,
            inputs=[video_input, ocr_engine_name, lang_preset, out_format, use_spellcheck],
            outputs=[output_file, preview_subs_box, progress_html]
        )
        
    return demo

def main():
    demo = build_gui()
    demo.launch(inbrowser=True, share=False)

if __name__ == "__main__":
    main()
