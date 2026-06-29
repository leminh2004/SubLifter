import os
import sys
import cv2
import numpy as np

# Add project root to python path so we can import sublifter
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sublifter.core.ocr_engine import OCREngine
from sublifter.core.video_processor import VideoProcessor
from sublifter.core.sub_writer import write_srt

def create_synthetic_video(output_path, width=640, height=360, fps=10, duration=5.0):
    """
    Creates a synthetic video with burned-in subtitles at the bottom.
    - 0s to 1s: Empty screen
    - 1s to 2.5s: "HELLO WORLD"
    - 2.5s to 3s: Empty screen
    - 3s to 4.5s: "SUBTITLE TESTING"
    - 4.5s to 5s: Empty screen
    """
    print(f"Creating synthetic video: {output_path}")
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    total_frames = int(fps * duration)
    for frame_idx in range(total_frames):
        timestamp = frame_idx / fps
        
        # Black frame
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Draw some background shapes to simulate a real video
        cv2.circle(frame, (width // 2, height // 2), 50, (100, 100, 100), -1)
        
        # Draw hardsub subtitles
        text = ""
        if 1.0 <= timestamp < 2.5:
            text = "HELLO WORLD"
        elif 3.0 <= timestamp < 4.5:
            text = "SUBTITLE TESTING"
            
        if text:
            # Subtitle styling: white text with a black outline
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 1.0
            thickness = 2
            
            # Get text size
            text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
            text_x = (width - text_size[0]) // 2
            text_y = int(height * 0.9)  # Bottom 90%
            
            # Draw black outline
            cv2.putText(frame, text, (text_x, text_y), font, font_scale, (0, 0, 0), thickness + 3, cv2.LINE_AA)
            # Draw white text
            cv2.putText(frame, text, (text_x, text_y), font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)
            
        out.write(frame)
        
    out.release()
    print("Synthetic video created successfully.")

def run_test():
    video_path = "test_video.mp4"
    output_srt = "test_output.srt"
    
    # 1. Create test video
    create_synthetic_video(video_path)
    
    # 2. Initialize SubLifter core components
    # We use 'en' language since our synthetic text is English
    print("Initializing OCREngine...")
    ocr = OCREngine(languages=['en'], confidence_threshold=0.2)
    
    # We set ymin=0.8 to focus on the bottom 20% of the video
    processor = VideoProcessor(
        ocr_engine=ocr,
        sample_rate=2.0,  # Process 2 frames per second
        ymin=0.8,
        ymax=1.0,
        xmin=0.0,
        xmax=1.0,
        diff_threshold=2.0
    )
    
    # 3. Extract subtitles
    print("Extracting subtitles...")
    subtitles = processor.process_video(video_path)
    
    print("\n--- Extracted Subtitles ---")
    for idx, sub in enumerate(subtitles, 1):
        print(f"#{idx} [{sub['start']:.2f}s -> {sub['end']:.2f}s]: {sub['text']}")
        
    # Write to SRT
    write_srt(subtitles, output_srt)
    print(f"Saved to: {output_srt}")
    
    # Cleanup test files
    if os.path.exists(video_path):
        os.remove(video_path)
        print("Cleaned up test video.")
        
    # Simple validation
    if len(subtitles) >= 2:
        print("\nTEST PASSED: Extracted at least 2 subtitle segments.")
        # Check text content (case-insensitive)
        text_1 = subtitles[0]['text'].upper()
        text_2 = subtitles[1]['text'].upper()
        if "HELLO" in text_1 and "WORLD" in text_1:
            print("Validation: Subtitle 1 matches successfully.")
        else:
            print(f"Warning: Subtitle 1 expected 'HELLO WORLD', got '{text_1}'")
            
        if "SUBTITLE" in text_2 or "TESTING" in text_2:
            print("Validation: Subtitle 2 matches successfully.")
        else:
            print(f"Warning: Subtitle 2 expected 'SUBTITLE TESTING', got '{text_2}'")
    else:
        print(f"\nTEST FAILED: Expected 2 subtitle segments, got {len(subtitles)}")
        sys.exit(1)

if __name__ == "__main__":
    run_test()
