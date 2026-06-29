import cv2
import numpy as np

class OCREngine:
    def __init__(self, languages=['vi', 'en'], confidence_threshold=0.35):
        """
        Initialize the OCR Engine.
        :param languages: List of language codes for EasyOCR (e.g., ['vi', 'en'])
        :param confidence_threshold: Ignore text detections with confidence lower than this
        """
        self.languages = languages
        self.confidence_threshold = confidence_threshold
        self.reader = None

    def _init_reader(self):
        """Lazy load EasyOCR reader to avoid importing cost on startup"""
        if self.reader is None:
            import easyocr
            import torch
            use_gpu = torch.cuda.is_available()
            print(f"[OCREngine] Khởi tạo EasyOCR. Trạng thái GPU: {use_gpu}")
            self.reader = easyocr.Reader(self.languages, gpu=use_gpu)

    def preprocess_image(self, img, mode='none'):
        """
        Preprocess frame for better OCR results.
        :param img: numpy array (BGR image)
        :param mode: Preprocessing mode ('none', 'binarize', 'adaptive', 'color_mask')
        """
        if mode == 'none':
            return img
            
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        if mode == 'binarize':
            # Increase contrast & Simple Otsu binarization
            gray = cv2.equalizeHist(gray)
            blur = cv2.GaussianBlur(gray, (3, 3), 0)
            _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            return thresh
            
        elif mode == 'adaptive':
            # Adaptive thresholding to extract text outline/strokes (black text on white background)
            thresh = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 81, 11
            )
            return thresh
            
        elif mode == 'color_mask':
            # HSV White/Yellow mask -> black text on white background
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            
            # White mask
            lower_white = np.array([0, 0, 180])
            upper_white = np.array([180, 40, 255])
            mask_white = cv2.inRange(hsv, lower_white, upper_white)
            
            # Yellow mask
            lower_yellow = np.array([10, 40, 120])
            upper_yellow = np.array([40, 255, 255])
            mask_yellow = cv2.inRange(hsv, lower_yellow, upper_yellow)
            
            # Combined mask
            mask = cv2.bitwise_or(mask_white, mask_yellow)
            
            # Create a clean white background
            clean_bg = np.ones_like(gray) * 255
            # Set text pixels to black
            clean_bg[mask > 0] = 0
            
            return clean_bg
            
        return gray

    def extract_text(self, img, preprocess_mode='none', width_ths=0.5) -> str:
        """
        Run OCR on the image and return the combined text.
        :param img: numpy array (BGR image)
        :param preprocess_mode: Preprocessing mode ('none', 'binarize', 'adaptive', 'color_mask')
        :param width_ths: Width merge threshold for word grouping (default: 0.5)
        """
        self._init_reader()
        
        # Preprocess
        processed = self.preprocess_image(img, mode=preprocess_mode)
        
        # Run EasyOCR
        # readtext accepts numpy arrays directly (both grayscale and BGR/RGB)
        results = self.reader.readtext(processed, width_ths=width_ths)
        
        if not results:
            return ""
            
        # Filter by confidence and sort by vertical position (Y coordinate of top-left)
        valid_results = []
        for bbox, text, conf in results:
            if conf >= self.confidence_threshold:
                # bbox format: [[x0, y0], [x1, y1], [x2, y2], [x3, y3]]
                top_left_y = bbox[0][1]
                top_left_x = bbox[0][0]
                valid_results.append((top_left_y, top_left_x, text.strip()))
                
        if not valid_results:
            return ""
            
        # Sort primarily by Y coordinate (vertical lines) then X coordinate
        # Group text that are roughly on the same horizontal line (within 10-15px difference)
        valid_results.sort(key=lambda x: (x[0], x[1]))
        
        # Group lines together
        lines = []
        current_line_y = None
        current_line_texts = []
        
        line_height_threshold = 15 # pixels threshold to group in the same line
        
        for y, x, text in valid_results:
            if not text:
                continue
            if current_line_y is None:
                current_line_y = y
                current_line_texts.append((x, text))
            elif abs(y - current_line_y) <= line_height_threshold:
                current_line_texts.append((x, text))
            else:
                # Flush previous line
                current_line_texts.sort(key=lambda item: item[0])
                lines.append(" ".join([item[1] for item in current_line_texts]))
                # Start new line
                current_line_y = y
                current_line_texts = [(x, text)]
                
        # Flush the last line
        if current_line_texts:
            current_line_texts.sort(key=lambda item: item[0])
            lines.append(" ".join([item[1] for item in current_line_texts]))
            
        # Combine lines with newlines
        full_text = "\n".join(lines)
        return full_text
