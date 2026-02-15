import re
import random


# ===== SPINTAX =====
# faqat single { } ni ushlaydi
SPINTAX_PATTERN = re.compile(r"\{([^{}]+)\}")


def parse_spintax(text: str) -> str:
    while True:
        match = SPINTAX_PATTERN.search(text)
        if not match:
            break

        # Agar ichida | yo‘q bo‘lsa bu spintax emas
        if "|" not in match.group(1):
            break

        options = match.group(1).split("|")
        text = text[: match.start()] + random.choice(options) + text[match.end() :]

    return text


# ===== PLACEHOLDER =====
PLACEHOLDER_PATTERN = re.compile(r"\{\{(.*?)\}\}")


def render_placeholders(text: str, context: dict) -> str:
    def replace(match):
        key = match.group(1).strip()
        return str(context.get(key, match.group(0)))

    return PLACEHOLDER_PATTERN.sub(replace, text)


# ===== MAIN =====
def render_text(raw_text: str, context: dict) -> str:
    text = parse_spintax(raw_text)
    text = render_placeholders(text, context)
    return text
