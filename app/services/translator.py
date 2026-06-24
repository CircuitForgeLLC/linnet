# app/services/translator.py — DeepL-backed tone label translation
#
# Translates short tone labels (e.g. "Neutral", "Stressed", "Apologetic")
# into the user's target language via the DeepL API.
#
# Two API key paths:
#   CF-managed (Paid tier): DEEPL_API_KEY env var (DeepL Pro endpoint)
#   BYOK (any tier):        per-session byok_deepl_key from StartRequest (DeepL Free endpoint)
#
# Per-session label cache: each unique label is translated once per session.
# Cache is discarded when the session ends — it lives on the Translator instance,
# which is created per-session and GC'd with the session.
#
# Rate limiting: translation runs only on ToneEvent emit, not on raw audio frames.
# The SSE generator calls translate() once per event; the cache makes repeat labels free.
from __future__ import annotations

import logging
import time

import requests

from app.config import settings

logger = logging.getLogger(__name__)

_DEEPL_FREE_URL = "https://api-free.deepl.com/v2/translate"
_DEEPL_PRO_URL = "https://api.deepl.com/v2/translate"


class Translator:
    """
    Per-session DeepL translator with label cache.

    Usage:
        translator = Translator.for_session(session)
        translated = translator.translate("Stressed")  # "Stressé" for target_lang="fr"
        translated = translator.translate("Stressed")  # cache hit — no API call
    """

    def __init__(
        self,
        target_lang: str,
        api_key: str,
        pro: bool = True,
    ) -> None:
        self._target_lang = target_lang.upper()  # DeepL uses uppercase codes
        self._api_key = api_key
        self._url = _DEEPL_PRO_URL if pro else _DEEPL_FREE_URL
        self._cache: dict[str, str] = {}

    @classmethod
    def for_session(cls, session) -> "Translator | None":
        """
        Create a Translator for a session, or return None if translation is disabled.

        Returns None when:
        - session.target_lang is empty
        - No API key is available (neither BYOK nor CF-managed)
        """
        target_lang = session.target_lang
        if not target_lang:
            return None

        byok = session.byok_deepl_key.strip()
        cf_key = settings.deepl_api_key.strip()

        if byok:
            return cls(target_lang=target_lang, api_key=byok, pro=False)
        if cf_key:
            return cls(target_lang=target_lang, api_key=cf_key, pro=True)

        logger.warning(
            "[translator] target_lang=%s set but no DeepL key available — skipping translation",
            target_lang,
        )
        return None

    def translate(self, label: str) -> str:
        """
        Translate a tone label. Returns the original label on any error.

        Results are cached per-session so the same label is only translated once.
        """
        if not label:
            return label

        if label in self._cache:
            return self._cache[label]

        translated = self._call_deepl(label)
        self._cache[label] = translated
        return translated

    def _call_deepl(self, text: str) -> str:
        try:
            resp = requests.post(
                self._url,
                headers={"Authorization": f"DeepL-Auth-Key {self._api_key}"},
                json={
                    "text": [text],
                    "target_lang": self._target_lang,
                },
                timeout=5,
            )
            if not resp.ok:
                logger.warning("[translator] DeepL returned %s for label %r", resp.status_code, text)
                return text
            data = resp.json()
            return data["translations"][0]["text"]
        except Exception as exc:
            logger.warning("[translator] DeepL call failed for label %r: %s", text, exc)
            return text
