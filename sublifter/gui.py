import gradio as gr
import cv2
import os
import sys
import numpy as np
from sublifter.core.ocr_engine import OCREngine
from sublifter.core.video_processor import VideoProcessor
from sublifter.core.sub_writer import write_srt, write_ass

def get_preview(video_path):
    """Generate a full frame with crop boundary overlay (85% centered horizontal, top+bottom 20% vertical)."""
    if not video_path or not os.path.exists(video_path):
        return None, None
        
    cap = cv2.VideoCapture(video_path)
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        return None, None
        
    h, w, _ = frame.shape
    
    # Fixed Coordinates:
    # Horizontal: 85% width centered -> xmin=0.075, xmax=0.925
    # Vertical: Top 20% (0.0 to 0.2) & Bottom 20% (0.8 to 1.0)
    x_start = int(w * 0.075)
    x_end = int(w * 0.925)
    y_top_end = int(h * 0.2)
    y_bottom_start = int(h * 0.8)
    
    overlay_frame = frame.copy()
    
    # Draw two red boxes for visual crop preview
    cv2.rectangle(overlay_frame, (x_start, 0), (x_end, y_top_end), (0, 0, 255), 3)
    cv2.rectangle(overlay_frame, (x_start, y_bottom_start), (x_end, h), (0, 0, 255), 3)
    
    # Crop and stack the two regions
    top_crop = frame[0:y_top_end, x_start:x_end]
    bottom_crop = frame[y_bottom_start:h, x_start:x_end]
    
    if top_crop.size > 0 and bottom_crop.size > 0:
        cropped = np.vstack([top_crop, bottom_crop])
    else:
        cropped = top_crop if top_crop.size > 0 else bottom_crop
        
    # Convert to RGB for Gradio
    overlay_frame = cv2.cvtColor(overlay_frame, cv2.COLOR_BGR2RGB)
    
    if cropped.size > 0:
        cropped_rgb = cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB)
    else:
        cropped_rgb = None
        
    return overlay_frame, cropped_rgb

def extract_subtitles(video_path, lang_preset, out_format, use_spellcheck, progress=gr.Progress()):
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
        ocr = OCREngine(languages=langs, confidence_threshold=0.35)
        
        # Fixed optimal settings under the hood:
        # - Horizontal: 85% width centered (xmin=0.075, xmax=0.925)
        # - Vertical: Top 20% + Bottom 20% (double_zone=True, ymin=0.8, ymax=1.0)
        processor = VideoProcessor(
            ocr_engine=ocr,
            sample_rate=1.5,
            ymin=0.8,
            ymax=1.0,
            xmin=0.075,
            xmax=0.925,
            diff_threshold=2.0,
            preprocess_mode='none',
            double_zone=True,
            width_ths=0.5,
            use_spellcheck=use_spellcheck,
            lang_preset=lang_preset
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
                cropped_preview = gr.Image(label="Khung hình phụ đề được cắt", interactive=False)
                
                gr.Markdown("### 📄 Kết quả")
                output_file = gr.File(label="Tải tệp phụ đề về máy")
                output_text = gr.Textbox(label="Xem trước phụ đề / Nhật ký xử lý", lines=15, max_lines=25)
                
        # Update preview when video is uploaded
        video_input.change(get_preview, inputs=[video_input], outputs=[preview_image, cropped_preview])
        
        # Click Run
        btn_run.click(
            extract_subtitles,
            inputs=[video_input, lang_preset, out_format, use_spellcheck],
            outputs=[output_file, output_text]
        )
        
    return demo

def main():
    demo = build_gui()
    # Launch locally
    demo.launch(inbrowser=True, share=False)

if __name__ == "__main__":
    main()
