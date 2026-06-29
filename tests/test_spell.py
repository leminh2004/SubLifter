import unittest
from sublifter.core.spell_checker import SpellCheckerPipeline

class TestSpellChecker(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("Đang khởi tạo SpellCheckerPipeline để kiểm thử...")
        cls.corrector = SpellCheckerPipeline()

    def test_word_segmentation(self):
        # Test splitting merged words
        self.assertEqual(self.corrector.correct("Pleasetakegoodcareofus"), "Please take good care of us")
        self.assertEqual(self.corrector.correct("Icareofus"), "I care of us")

    def test_spelling_correction(self):
        # Test single word spelling correction
        self.assertEqual(self.corrector.correct("talec"), "take")
        self.assertEqual(self.corrector.correct("goodc"), "good")
        self.assertEqual(self.corrector.correct("nervouss"), "nervous")

    def test_romaji_preservation(self):
        # Test that Japanese Romaji names and terms are preserved
        self.assertEqual(self.corrector.correct("Aqours"), "Aqours")
        self.assertEqual(self.corrector.correct("Saito Shuka"), "Saito Shuka")
        self.assertEqual(self.corrector.correct("Kimi no Na wa"), "Kimi no Na wa")
        self.assertEqual(self.corrector.correct("watashi"), "watashi")
        self.assertEqual(self.corrector.correct("yume"), "yume")
        self.assertEqual(self.corrector.correct("Chika"), "Chika")
        self.assertEqual(self.corrector.correct("Dia"), "Dia")

    def test_mixed_languages(self):
        # Test mixed English + Vietnamese sentences
        # Should correct English but leave Vietnamese intact
        text = "Chào mọi người (Goodmoming, please taecareofus)"
        expected = "Chào mọi người (Good morning, please take care of us)"
        self.assertEqual(self.corrector.correct(text), expected)

        # Test mixed Japanese Romaji + English
        text = "Welcome to Numazu, Aqours are performing here!"
        expected = "Welcome to Numazu, Aqours are performing here!"
        self.assertEqual(self.corrector.correct(text), expected)

if __name__ == "__main__":
    unittest.main()
