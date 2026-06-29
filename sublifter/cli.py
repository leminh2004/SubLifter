import argparse
import os
import sys
from tqdm import tqdm
from sublifter.core.ocr_engine import OCREngine
from sublifter.core.video_processor import VideoProcessor
from sublifter.core.sub_writer import write_srt, write_ass

def main():
    parser = argparse.ArgumentParser(description="SubLifter - Hardsub Extractor CLI Tool")
    parser.add_argument("-i", "--input", required=True, help="Path to input video file")
    parser.add_argument("-o", "--output", help="Path to output subtitle file (default: same folder as video)")
    parser.add_argument("-f", "--format", choices=["srt", "ass"], default="srt", help="Output subtitle format (default: srt)")
    parser.add_argument("-l", "--languages", default="vi,en", help="Comma-separated language codes for OCR, e.g. vi,en (default: vi,en)")
    parser.add_argument("--sample-rate", type=float, default=1.5, help="Frames to process per second (default: 1.5)")
    parser.add_argument("--ymin", type=float, default=0.8, help="Top crop boundary percentage [0.0 to 1.0] (default: 0.8)")
    parser.add_argument("--ymax", type=float, default=1.0, help="Bottom crop boundary percentage [0.0 to 1.0] (default: 1.0)")
    parser.add_argument("--xmin", type=float, default=0.0, help="Left crop boundary percentage [0.0 to 1.0] (default: 0.0)")
    parser.add_argument("--xmax", type=float, default=1.0, help="Right crop boundary percentage [0.0 to 1.0] (default: 1.0)")
    parser.add_argument("--diff-threshold", type=float, default=2.0, help="Pixel difference threshold to trigger OCR. Set to 0 to run OCR on all sampled frames (default: 2.0)")
    parser.add_argument("-c", "--conf", type=float, default=0.35, help="OCR confidence threshold [0.0 to 1.0] (default: 0.35)")
    parser.add_argument("--preprocess", choices=["none", "binarize", "adaptive", "color_mask"], default="none", help="Preprocessing method for image cleaning (default: none)")
    parser.add_argument("--width-ths", type=float, default=0.5, help="Width merge threshold for word grouping (default: 0.5)")
    parser.add_argument("--no-spellcheck", action="store_true", help="Vô hiệu hóa tự động sửa lỗi chính tả và cách từ (Spell Checker)")

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Lỗi: Không tìm thấy tệp video đầu vào tại '{args.input}'", file=sys.stderr)
        sys.exit(1)

    # Resolve output path
    output_path = args.output
    if not output_path:
        base, _ = os.path.splitext(args.input)
        output_path = f"{base}.{args.format}"

    # Parse languages
    langs = [lang.strip() for lang in args.languages.split(",")]
    use_spellcheck = not args.no_spellcheck
    
    print("=" * 60)
    print("Bắt đầu trích xuất phụ đề cứng SubLifter")
    print(f"Video đầu vào  : {args.input}")
    print(f"Tệp đầu ra     : {output_path}")
    print(f"Ngôn ngữ       : {langs}")
    print(f"Sửa chính tả   : {'Bật' if use_spellcheck else 'Tắt'}")
    print(f"Vùng cắt (Crop): Y: [{args.ymin:.2f} - {args.ymax:.2f}], X: [{args.xmin:.2f} - {args.xmax:.2f}]")
    print(f"Tốc độ quét    : {args.sample_rate} Hz (mỗi {1/args.sample_rate:.2f} giây)")
    print(f"Ngưỡng lệch    : {args.diff_threshold}")
    print(f"Tiền xử lý     : {args.preprocess}")
    print(f"Ngưỡng gộp từ  : {args.width_ths}")
    print("=" * 60)
    
    print("Đang khởi tạo OCREngine (EasyOCR)... (Quá trình này có thể mất một chút thời gian để tải mô hình)")
    ocr = OCREngine(languages=langs, confidence_threshold=args.conf)
    
    processor = VideoProcessor(
        ocr_engine=ocr,
        sample_rate=args.sample_rate,
        ymin=args.ymin,
        ymax=args.ymax,
        xmin=args.xmin,
        xmax=args.xmax,
        diff_threshold=args.diff_threshold,
        preprocess_mode=args.preprocess,
        width_ths=args.width_ths,
        use_spellcheck=use_spellcheck,
        lang_preset=args.languages
    )

    pbar = tqdm(total=100, desc="Đang trích xuất phụ đề", bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {postfix}]")

    def progress_callback(progress, status_text):
        percent = int(progress * 100)
        pbar.n = percent
        pbar.set_postfix_str(status_text)
        pbar.refresh()

    try:
        subtitles = processor.process_video(args.input, progress_callback=progress_callback)
        pbar.n = 100
        pbar.set_postfix_str("Hoàn thành!")
        pbar.refresh()
        pbar.close()
        
        print(f"\nĐã trích xuất {len(subtitles)} đoạn phụ đề.")
        
        # Write to file
        if args.format == "srt":
            write_srt(subtitles, output_path)
        else:
            write_ass(subtitles, output_path)
            
        print(f"Phụ đề đã được lưu thành công tại: {output_path}")
        
    except Exception as e:
        pbar.close()
        print(f"\nĐã xảy ra lỗi trong quá trình trích xuất: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
