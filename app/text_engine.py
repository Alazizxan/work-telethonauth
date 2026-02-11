import re
import random


def parse_spintax(text: str) -> str:
    pattern = re.compile(r"\{([^{}]+)\}")

    while True:
        match = pattern.search(text)
        if not match:
            break

        options = match.group(1).split("|")
        text = text[:match.start()] + random.choice(options) + text[match.end():]

    return text


def render_placeholders(text: str, context: dict) -> str:
    for key, value in context.items():
        text = text.replace(f"{{{key}}}", str(value))
    return text


def render_text(raw_text: str, context: dict) -> str:
    text = parse_spintax(raw_text)
    text = render_placeholders(text, context)
    return text
