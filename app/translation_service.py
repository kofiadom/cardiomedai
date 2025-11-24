import os
import asyncio
from typing import Optional
from ghana_nlp import GhanaNLP


class TranslationService:
    """
    Service class for handling text translation using GhanaNLP API.
    Supports translation between English and African languages like Twi, Ga, Ewe, etc.
    """

    def __init__(self, api_key: str = None):
        """
        Initialize the translation service with GhanaNLP API key.

        Args:
            api_key: GhanaNLP API key. If not provided, will look for GHANA_NLP_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("GHANA_NLP_API_KEY")
        if not self.api_key:
            raise ValueError(
                "GhanaNLP API key not provided. Please set GHANA_NLP_API_KEY environment variable "
                "or pass api_key parameter."
            )

        self.nlp = GhanaNLP(api_key=self.api_key)

    async def translate_to_language(
        self,
        text: str,
        target_language: str = "tw"
    ) -> Optional[str]:
        """
        Translate text from English to the target language.

        Args:
            text: The English text to translate
            target_language: Target language code (default: "tw" for Twi)
                           - "tw": Twi
                           - "gaa": Ga
                           - "ee": Ewe
                           - "fat": Fante
                           - "dag": Dagbani

        Returns:
            Translated text or None if translation fails
        """
        try:
            if not text or not text.strip():
                return None

            # GhanaNLP expects language pair in format "en-xx" where xx is target language
            language_pair = f"en-{target_language}"

            # Run the translation in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.nlp.translate(text, language_pair=language_pair)
            )

            # Handle the result - GhanaNLP returns different formats
            if isinstance(result, dict):
                # If result is a dict, extract the translated text
                return result.get("translated_text") or result.get("text") or str(result)
            else:
                # If it's a string or other type, return as is
                return str(result) if result else None

        except Exception as e:
            print(f"⚠️ Translation failed for language {target_language}: {str(e)}")
            return None

    async def translate_health_advice(
        self,
        advice_text: str,
        target_language: str = "tw"
    ) -> dict:
        """
        Translate health advisor advice to the target language.

        Args:
            advice_text: The health advice response to translate
            target_language: Target language code (default: "tw")

        Returns:
            Dictionary with original and translated text
        """
        translated_text = await self.translate_to_language(advice_text, target_language)

        return {
            "original": advice_text,
            "translated": translated_text,
            "language": target_language,
            "success": translated_text is not None
        }


# Supported language codes
SUPPORTED_LANGUAGES = {
    "en": "English",
    "tw": "Twi",
    "gaa": "Ga",
    "ee": "Ewe",
    "fat": "Fante",
    "dag": "Dagbani"
}


def get_supported_languages() -> dict:
    """Get all supported languages with their codes and names."""
    return SUPPORTED_LANGUAGES
