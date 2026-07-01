import cv2
import numpy as np
import difflib
import time
from .sub_writer import write_srt, write_ass
from .spell_checker import SpellCheckerPipeline

def get_text_similarity(str1: str, str2: str) -> float:
    """Calculate similarity ratio between two strings, ignoring spaces and case."""
    s1 = "".join(str1.lower().split())
    s2 = "".join(str2.lower().split())
    return difflib.SequenceMatcher(None, s1, s2).ratio()

class VideoProcessor:
    def __init__(self, ocr_engine, sample_rate=2.0, ymin=0.8, ymax=1.0, xmin=0.0, xmax=1.0, diff_threshold=2.0, preprocess_mode='none', double_zone=False, width_ths=0.5, use_spellcheck=True, lang_preset=""):
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
        :param double_zone: If True, crops and stacks both top 20% and bottom 20%
        :param width_ths: Width merge threshold for EasyOCR (default: 0.5)
        :param use_spellcheck: Enable/disable real-time spell check
        :param lang_preset: Language preset name
        """
        self.ocr_engine = ocr_engine
        self.sample_rate = sample_rate
        self.ymin = ymin
        self.ymax = ymax
        self.xmin = xmin
        self.xmax = xmax
        self.diff_threshold = diff_threshold
        self.preprocess_mode = preprocess_mode
        self.double_zone = double_zone
        self.width_ths = width_ths
        self.use_spellcheck = use_spellcheck
        self.lang_preset = lang_preset
        self.spell_checker = SpellCheckerPipeline() if use_spellcheck else None

    def process_video_yield(self, video_path: str):
        """
        Process the video and yield progress (progress_ratio, elapsed_seconds, eta_seconds, preview_subtitles).
        """
        import tempfile
        import shutil
        import os
        
        # Create a temporary copy to avoid locking the original file on Windows
        temp_dir = tempfile.gettempdir()
        temp_video_path = os.path.join(temp_dir, f"sublifter_process_{os.path.basename(video_path)}")
        try:
            shutil.copy2(video_path, temp_video_path)
        except Exception:
            temp_video_path = video_path
            
        cap = cv2.VideoCapture(temp_video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {video_path}")

        try:
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            if fps <= 0 or total_frames <= 0:
                raise ValueError("Invalid video file metadata (FPS or frame count is zero).")

            duration = total_frames / fps
            step = max(1, int(fps / self.sample_rate))
            self.fps = fps
            self.step = step
            
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
            prev_text = ""
            
            current_frame = 0
            start_time = time.time()
            
            while current_frame < total_frames:
                if not cap.grab():
                    break
                
                if current_frame % step == 0:
                    ret, frame = cap.retrieve()
                    if ret:
                        timestamp = current_frame / fps
                        
                        # Crop the subtitle region
                        if self.double_zone:
                            y_top_end = int(height * 0.2)
                            y_bottom_start = int(height * 0.8)
                            top_crop = frame[0:y_top_end, x_start:x_end]
                            bottom_crop = frame[y_bottom_start:height, x_start:x_end]
                            if top_crop.size > 0 and bottom_crop.size > 0:
                                cropped = np.vstack([top_crop, bottom_crop])
                            else:
                                cropped = frame[y_start:y_end, x_start:x_end]
                        else:
                            cropped = frame[y_start:y_end, x_start:x_end]
                        
                        if cropped.size > 0:
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
                                text = self.ocr_engine.extract_text(cropped, preprocess_mode=self.preprocess_mode, width_ths=self.width_ths)
                                if self.use_spellcheck and text and self.spell_checker:
                                    text = self.spell_checker.correct(text, self.lang_preset)
                            else:
                                # Re-use previous text if difference is negligible
                                text = prev_text
                            
                            prev_text = text

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
                            progress = current_frame / total_frames
                            elapsed = time.time() - start_time
                            eta = (elapsed / progress - elapsed) if progress > 0 else 0
                            
                            # Combine active subtitle with accumulated subtitles for preview
                            preview_subs = list(subtitles)
                            if active_sub:
                                preview_subs.append(active_sub)
                                
                            yield progress, elapsed, eta, preview_subs
                
                current_frame += 1

            # Flush the last active subtitle if any
            if active_sub:
                subtitles.append(active_sub)

            # Post-process subtitles to merge very close blocks and remove noise
            cleaned_subtitles = self._clean_subtitles(subtitles)
            yield 1.0, time.time() - start_time, 0.0, cleaned_subtitles
        finally:
            cap.release()
            del cap
            import gc
            gc.collect()
            import os
            if 'temp_video_path' in locals() and temp_video_path != video_path and os.path.exists(temp_video_path):
                try:
                    os.remove(temp_video_path)
                except Exception:
                    pass

    def process_video(self, video_path: str, progress_callback=None):
        """
        Process the video and extract subtitles. Returns the final list of subtitles.
        """
        subtitles = []
        for progress, elapsed, eta, current_subs in self.process_video_yield(video_path):
            subtitles = current_subs
            if progress_callback:
                try:
                    progress_callback(progress, elapsed, eta, current_subs)
                except TypeError:
                    mins = int(eta // 60)
                    secs = int(eta % 60)
                    progress_callback(progress, f"Còn lại: {mins:02d}:{secs:02d}")
        return subtitles

    def _clean_subtitles(self, subtitles):
        """Merge adjacent subtitles with identical text and filter out short empty noise."""
        if not subtitles:
            return []
            
        merged = []
        current = subtitles[0]
        
        fps = getattr(self, 'fps', 30.0)
        step = getattr(self, 'step', 20)
        one_frame_duration = step / fps
        
        for next_sub in subtitles[1:]:
            gap = next_sub['start'] - current['end']
            txt1 = current['text'].strip()
            txt2 = next_sub['text'].strip()
            similarity = get_text_similarity(txt1, txt2)
            
            # Check for substring relationship (useful for typewriter / cumulative / karaoke subs)
            is_substring = False
            if len(txt1) >= 4 and len(txt2) >= 4:
                is_substring = (txt1 in txt2) or (txt2 in txt1)
                
            # Merge conditions:
            # 1. Very close in time (gap < 0.8s) AND (similarity > 0.70 OR is_substring)
            # 2. Or overlapping/same frame (gap < 0) AND (similarity > 0.60 OR is_substring)
            should_merge = False
            if gap < 0.8:
                if similarity > 0.70 or is_substring:
                    should_merge = True
            elif gap < 0: # Overlapping
                if similarity > 0.60 or is_substring:
                    should_merge = True
            
            if should_merge:
                current['end'] = max(current['end'], next_sub['end'])
                # Select the longer/better text
                if len(txt2) > len(txt1):
                    current['text'] = next_sub['text']
            else:
                merged.append(current)
                current = next_sub
                
        merged.append(current)
        
        # Filter out subtitles that are extremely short or have empty/noise text
        final_subs = []
        for sub in merged:
            duration = sub['end'] - sub['start']
            text = sub['text'].strip()
            if not text:
                continue
                
            # Filter out single-frame transient noise (e.g. single letters/symbols or numbers)
            clean_txt = "".join([c for c in text if c.isalnum()])
            if duration <= one_frame_duration + 0.15:
                if len(clean_txt) <= 2 or clean_txt.isdigit():
                    continue
                    
            if duration >= 0.3:
                final_subs.append(sub)
                
        return final_subs
