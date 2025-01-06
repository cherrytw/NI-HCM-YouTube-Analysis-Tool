# translator.py
from deep_translator import GoogleTranslator
from langdetect import detect, LangDetectException


class TranslationService:
    @staticmethod
    def detect_language(text):
        try:
            return detect(text)
        except LangDetectException:
            return "unknown"

    @staticmethod
    def translate_to_english(text):
        try:
            source_lang = detect(text)
            if source_lang == "en":
                return text, source_lang

            translator = GoogleTranslator(source=source_lang, target="en")
            translated_text = translator.translate(text)
            return translated_text, source_lang
        except Exception as e:
            print(f"Translation error: {str(e)}")
            return text, "en"
