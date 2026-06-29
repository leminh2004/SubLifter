import cv2
import numpy as np
import difflib
from .sub_writer import write_srt, write_ass

def get_text_similarity(str1: str, str2: str) -> float:
    """Calculate similarity ratio between two strings."""
    return difflib.SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

class VideoProcessor:
    def __init__(self, ocr_engine, sample_rate=2.0, ymin=0.8, ymax=1.0, xmin=0.0, xmax=1.0, diff_threshold=2.0, preprocess_mode='none'):
        """
        Initialize Video Processor.
        :param ocr_engine: An instance of OCREngine
        :param sample_rate: How many frames to process per second (e.g. 2.0 means every 0.5s)
        :param ymin: Top boundary percentage (0.0 to 1.0)
        :param ymax: Bottom boundary percentage (0.0 to 1.0)
        :param xmin: Left boundary percentage (0.0 to 1.0)
        :param xmax: Right boundary percentage (0.0 to 1.0)
        :param diff_threshold: Pixel difference threshold to trigger OCR. Set to 0 to run OCR on all sampled frames.
        :param preprocess_mode: Preprocessing mode ('none', 'binarize', 'adaptive', 'color_mask')
        """
        self.ocr_engine = ocr_engine
        self.sample_rate = sample_rate
        self.ymin = ymin
        self.ymax = ymax
        self.xmin = xmin
        self.xmax = xmax
        self.diff_threshold = diff_threshold
        self.preprocess_mode = preprocess_mode

    def process_video(self, video_path: str, progress_callback=None):
        """
        Process the video and extract subtitles.
        Yields progress (0.0 to 1.0) and current status text if progress_callback is not provided.
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        if fps <= 0 or total_frames <= 0:
            raise ValueError("Invalid video file metadata (FPS or frame count is zero).")

        duration = total_frames / fps
        step = max(1, int(fps / self.sample_rate))
        
        # Crop coordinates in pixels
        y_start = int(height * self.ymin)
        y_end = int(height * self.ymax)
        x_start = int(width * self.xmin)
        x_end = int(width * self.xmax)

        # Enforce valid coordinates
        y_start, y_end = max(0, y_start), min(height, y_end)
        x_start, x_end = max(0, x_start), min(width, x_end)

        subtitles = []
        active_sub = None
        
        prev_norm_frame = None
        
        frame_idx = 0
        
        while frame_idx < total_frames:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret:
                break
                
            timestamp = frame_idx / fps
            
            # Crop the subtitle region
            cropped = frame[y_start:y_end, x_start:x_end]
            if cropped.size == 0:
                frame_idx += step
                continue
                
            # Normalize cropped frame (grayscale & fixed size for change detection)
            norm_w, norm_h = 320, 80
            gray_cropped = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
            norm_frame = cv2.resize(gray_cropped, (norm_w, norm_h))
            
            # Detect pixel difference
            should_run_ocr = True
            if self.diff_threshold > 0 and prev_norm_frame is not None:
                # Calculate mean absolute difference
                diff = cv2.absdiff(norm_frame, prev_norm_frame)
                mean_diff = np.mean(diff)
                if mean_diff < self.diff_threshold:
                    should_run_ocr = False
            
            prev_norm_frame = norm_frame
            
            # Extract text
            if should_run_ocr:
                text = self.ocr_engine.extract_text(cropped, preprocess_mode=self.preprocess_mode)
            else:
                # Re-use previous text if difference is negligible
                text = active_sub['text'] if active_sub else ""

            # Manage subtitle states
            if text:
                if active_sub:
                    similarity = get_text_similarity(active_sub['text'], text)
                    if similarity > 0.65:
                        # Extend current subtitle
                        active_sub['end'] = timestamp + (step / fps)
                    else:
                        # Text changed, save previous and start new
                        subtitles.append(active_sub)
                        active_sub = {
                            'start': timestamp,
                            'end': timestamp + (step / fps),
                            'text': text
                        }
                else:
                    # New subtitle starts
                    active_sub = {
                        'start': timestamp,
                        'end': timestamp + (step / fps),
                        'text': text
                    }
            else:
                # No text detected
                if active_sub:
                    subtitles.append(active_sub)
                    active_sub = None
            
            # Progress reporting
            progress = frame_idx / total_frames
            if progress_callback:
                progress_callback(progress, f"Đang xử lý: {timestamp:.1f}giây / {duration:.1f}giây")
            
            frame_idx += step

        # Flush the last active subtitle if any
        if active_sub:
            subtitles.append(active_sub)

        cap.release()
        
        # Post-process subtitles to merge very close blocks and remove noise
        cleaned_subtitles = self._clean_subtitles(subtitles)
        return cleaned_subtitles

    def _clean_subtitles(self, subtitles):
        """Merge adjacent subtitles with identical text and filter out short empty noise."""
        if not subtitles:
            return []
            
        merged = []
        current = subtitles[0]
        
        for next_sub in subtitles[1:]:
            # If gap between subtitles is less than 0.5s and texts are similar, merge them
            gap = next_sub['start'] - current['end']
            similarity = get_text_similarity(current['text'], next_sub['text'])
            
            if gap < 0.5 and similarity > 0.8:
                # Keep the longer text or current text, and extend the end time
                current['end'] = next_sub['end']
                if len(next_sub['text']) > len(current['text']):
                    current['text'] = next_sub['text']
            else:
                merged.append(current)
                current = next_sub
                
        merged.append(current)
        
        # Filter out subtitles that are extremely short (e.g. < 0.2s) or have empty text
        final_subs = []
        for sub in merged:
            duration = sub['end'] - sub['start']
            text = sub['text'].strip()
            # Remove very short duration blocks that might be transient noise
            if duration >= 0.3 and len(text) > 0:
                final_subs.append(sub)
                
        return final_subs
