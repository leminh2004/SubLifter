import re
import string
from spellchecker import SpellChecker
import wordsegment as ws

# Custom whitelist of Japanese Romaji names, terms, and short particles
ROMAJI_WHITELIST = {
    # Aqours and Love Live! terms
    'aqours', 'lovelive', 'muse', 'nijigasaki', 'liella', 'hasunosora', 'school', 'idol',
    'chika', 'riko', 'kanan', 'dia', 'you', 'yoshiko', 'yohane', 'hanamaru', 'mari', 'ruby',
    'anju', 'inami', 'rikako', 'aida', 'nanaka', 'suwa', 'arisa', 'komiya', 'shuka', 'saito',
    'aika', 'kobayashi', 'kanako', 'takatsuki', 'aina', 'suzuki', 'ai', 'furihata',
    # BanG Dream! terms
    'bang', 'dream', 'roselia', 'poppinparty', 'morfonica', 'ras', 'pastelpalettes', 'afterglow',
    'hellohappyworld', 'kasumi', 'ran', 'yukina', 'kokoro', 'aya', 'mygo', 'avemujica',
    # Common Romaji names and places
    'numazu', 'tokyo', 'japan', 'saito', 'shuka', 'aida', 'rikako', 'inami', 'anju',
    # Japanese particles and short Romaji words (2 letters) to protect from English spellcheck
    'wa', 'no', 'ni', 'de', 'to', 'ga', 'wo', 'he', 'yo', 'ne', 'ka', 'na', 'ma', 'ta', 'te', 're', 'su',
    # Software names
    'sublifter', 'gradio', 'easyocr'
}

# Regex to detect standard Japanese Romaji syllables (Consonant + Vowel structure)
# - Consonants: k, s, t, n, h, m, y, r, w, g, z, d, b, p, sh, ch, ts, ky, sy, hy, my, ry, gy, by, py
# - Vowels: a, i, u, e, o (single or double)
# - Plus nasal 'n' (not followed by a vowel)
ROMAJI_PATTERN = re.compile(
    r'^(?:(?:[kstnhmyrwgzdbp]|sh|ch|ts|ky|sy|hy|my|ry|gy|by|py)?(?:[aeiou]{1,2}|y[aeou]|[aeiou]n\b|n(?![aeiou])))+$',
    re.IGNORECASE
)

# Common Vietnamese syllables to bypass English spellcheck
VIETNAMESE_SYLLABLES = {
    'anh', 'em', 'yeu', 'thuong', 'chao', 'xin', 'cam', 'on', 'khi', 'cho', 'nha', 'hoc', 'sinh',
    'truong', 'lop', 'thay', 'co', 'ban', 'toi', 'chung', 'ta', 'co', 'the', 'lam', 'duoc', 'muon',
    'viet', 'nam', 'tieng', 'nguoi', 'di', 'den', 've', 'ra', 'vao', 'len', 'xuong', 'chay', 'nhanh',
    'cham', 'dep', 'xau', 'vui', 'buon', 'khoc', 'cuoi', 'ngay', 'dem', 'sang', 'trua', 'chieu', 'toi',
    'mot', 'hai', 'ba', 'bon', 'nam', 'sau', 'bay', 'tam', 'chin', 'muoi', 'tram', 'nghin', 'trieu'
}

# Known OCR error replacements (specifically mapping common OCR failures to correct words)
OCR_ERRORS_MAP = {
    'talec': 'take',
    'goodc': 'good',
    'moming': 'morning',
    'goodmoming': 'good morning',
    'earlied': 'earlier',
    'eailier': 'earlier',
    'piease': 'please',
    'piase': 'please',
    'plase': 'please',
    'pleasetakegoodcaredus': 'please take good care of us',
    'pleasetakegoodcaredfus': 'please take good care of us',
    'pleasetakegoodcares': 'please take good care of us',
    'pleasetakegoodcareofus': 'please take good care of us',
    'pieasetalegoodcareofus': 'please take good care of us',
    'plasetalegood': 'please take good',
    'taecareofus': 'take care of us',
    'icareofus': 'i care of us',
    'goodimorning': 'good morning',
    'cumeon': 'come on',
    'omeonin': 'come on in',
    'lmsonervous': "i'm so nervous",
    'maliilenervous': 'a little nervous',
    'imalittlneruous': "i'm a little nervous",
    'imalittleneruous': "i'm a little nervous",
    'fmalittleneruous': "i'm a little nervous",
    'threemonthsearlier': 'three months earlier',
    'onemonthearlier': 'one month earlier',
    'sunshinell': 'sunshine',
    'hinel': 'shine',
    'vaqours': 'aqours',
}

class SpellCheckerPipeline:
    def __init__(self):
        # Initialize English spell checker
        self.spell = SpellChecker(language='en')
        
        # Load wordsegment model
        ws.load()
        
        # Add whitelists to spellcheck dictionary so they are recognized as valid words
        self.spell.word_frequency.load_words(list(ROMAJI_WHITELIST))
        self.spell.word_frequency.load_words(list(VIETNAMESE_SYLLABLES))

        # Pre-compile patterns for OCR replacements
        self.ocr_patterns = []
        for key, val in OCR_ERRORS_MAP.items():
            pattern = re.compile(r'\b' + re.escape(key) + r'\b', re.IGNORECASE)
            self.ocr_patterns.append((pattern, val))

    def _is_vietnamese(self, word: str) -> bool:
        viet_diacritics = "áàảãạâấầẩẫậăắằẳẵặéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđ"
        if any(c in viet_diacritics for c in word.lower()):
            return True
        if word.lower() in VIETNAMESE_SYLLABLES:
            return True
        return False

    def _is_romaji(self, word: str) -> bool:
        w_lower = word.lower()
        if w_lower in ROMAJI_WHITELIST:
            return True
        # Check if it fits Japanese Romaji syllable pattern
        if len(w_lower) >= 3 and ROMAJI_PATTERN.match(w_lower):
            # Avoid matching common English words that fit the pattern
            if self.spell.known([w_lower]):
                return False
            return True
        return False

    def _match_case(self, original: str, corrected: str) -> str:
        """Restore the casing of the original word onto the corrected word."""
        if original.isupper():
            return corrected.upper()
        if original and original[0].isupper():
            # Only capitalize the first word of the correction (natural sentence capitalization)
            words = corrected.split()
            if words:
                words[0] = words[0].capitalize()
                for i in range(1, len(words)):
                    words[i] = words[i].lower()
                return " ".join(words)
        return corrected.lower()

    def _pre_clean_ocr(self, text: str) -> str:
        """Replace known common OCR typos and errors before spelling checking."""
        for pattern, replacement in self.ocr_patterns:
            def replace_match(match):
                matched_text = match.group(0)
                return self._match_case(matched_text, replacement)
            text = pattern.sub(replace_match, text)
        return text

    def correct_word(self, word: str) -> str:
        """Correct a single clean word (without punctuation)."""
        if not word or not word.isalpha():
            return word

        # 1. Skip if it is Vietnamese or Romaji
        if self._is_vietnamese(word) or self._is_romaji(word):
            return word

        # 2. Skip if it is already a known English word
        w_lower = word.lower()
        if self.spell.known([w_lower]):
            return word

        # 3. Check if it's a simple typo (edit distance <= 1, e.g. 'nervouss' -> 'nervous')
        # We prefer this over wordsegment to avoid splitting simple typos like 'nervouss' into 'nervous s'
        corr = self.spell.correction(w_lower)
        if corr and corr != w_lower and abs(len(w_lower) - len(corr)) <= 1:
            return self._match_case(word, corr)

        # 4. Try to segment if it is a long concatenated word (e.g. 'Icareofus')
        if len(w_lower) > 5:
            segmented = ws.segment(w_lower)
            if len(segmented) > 1:
                # Correct each word in the segment as an English word
                corrected_segments = []
                for seg in segmented:
                    if not self.spell.known([seg]):
                        c = self.spell.correction(seg)
                        corrected_segments.append(c if c else seg)
                    else:
                        corrected_segments.append(seg)
                
                # Reconstruct spacing
                joined = " ".join(corrected_segments)
                return self._match_case(word, joined)

        # 5. Fallback correction for other typos
        if corr and corr != w_lower:
            return self._match_case(word, corr)

        return word

    def correct(self, text: str, lang_preset: str = "") -> str:
        """Correct spelling and spacing in a sentence, preserving CJK characters."""
        if not text:
            return text

        # 1. Apply pre-clean OCR rules
        text = self._pre_clean_ocr(text)

        # 2. Tokenize by keeping whitespaces and punctuation boundaries
        tokens = re.split(r'([^a-zA-Záàảãạâấầẩẫậăắằẳẵặéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđ]+)', text)
        
        corrected_tokens = []
        for token in tokens:
            if not token:
                continue
            # If the token contains letters, try to correct it
            if re.match(r'^[a-zA-Záàảãạâấầẩẫậăắằẳẵặéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđ]+$', token):
                corrected_tokens.append(self.correct_word(token))
            else:
                corrected_tokens.append(token)
                
        return "".join(corrected_tokens)
