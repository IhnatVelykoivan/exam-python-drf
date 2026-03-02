import os
import re

from django.conf import settings

_PROFANITY_WORDS = None


def _load_profanity_words():
    global _PROFANITY_WORDS
    if _PROFANITY_WORDS is None:
        words_path = os.path.join(settings.BASE_DIR, 'profanity', 'words.txt')
        with open(words_path, 'r', encoding='utf-8') as f:
            content = f.read()
        # Handle both "one word per line" and "space-separated" formats
        _PROFANITY_WORDS = [
            w.lower() for w in content.split() if w.strip()
        ]
    return _PROFANITY_WORDS


def check_profanity(text):
    """
    Check if text contains profanity.
    Returns True if profanity found, False otherwise.
    """
    words = _load_profanity_words()
    text_lower = text.lower()
    for word in words:
        if re.search(r'\b' + re.escape(word) + r'\b', text_lower):
            return True
    return False
