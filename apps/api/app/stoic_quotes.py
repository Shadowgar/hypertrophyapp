from __future__ import annotations

from datetime import date
import hashlib
from typing import TypedDict


class StoicQuote(TypedDict):
    text: str
    author: str
    source: str


MARCUS = "Marcus Aurelius"
EPICTETUS = "Epictetus"
SENECA = "Seneca"

MEDITATIONS = "Meditations"
DISCOURSES = "Discourses"
LETTERS = "Letters"


_QUOTES: tuple[StoicQuote, ...] = (
    {"text": "You have power over your mind, not outside events.", "author": MARCUS, "source": MEDITATIONS},
    {"text": "The impediment to action advances action. What stands in the way becomes the way.", "author": MARCUS, "source": MEDITATIONS},
    {"text": "Waste no more time arguing what a good person should be. Be one.", "author": MARCUS, "source": MEDITATIONS},
    {"text": "If it is not right, do not do it; if it is not true, do not say it.", "author": MARCUS, "source": MEDITATIONS},
    {"text": "You become what you give your attention to.", "author": EPICTETUS, "source": DISCOURSES},
    {"text": "No person is free who is not master of themselves.", "author": EPICTETUS, "source": DISCOURSES},
    {"text": "First say to yourself what you would be; and then do what you have to do.", "author": EPICTETUS, "source": DISCOURSES},
    {"text": "Difficulty shows what people are.", "author": EPICTETUS, "source": DISCOURSES},
    {"text": "We suffer more in imagination than in reality.", "author": SENECA, "source": LETTERS},
    {"text": "Luck is what happens when preparation meets opportunity.", "author": SENECA, "source": LETTERS},
    {"text": "Begin at once to live, and count each day as a separate life.", "author": SENECA, "source": LETTERS},
    {"text": "No great thing is created suddenly.", "author": EPICTETUS, "source": DISCOURSES},
    {"text": "The soul becomes dyed with the color of its thoughts.", "author": MARCUS, "source": MEDITATIONS},
    {"text": "Do not explain your philosophy. Embody it.", "author": EPICTETUS, "source": DISCOURSES},
    {"text": "How long are you going to wait before you demand the best for yourself?", "author": EPICTETUS, "source": "Enchiridion"},
    {"text": "No person can have a peaceful life who thinks too much about length of it.", "author": SENECA, "source": "On the Shortness of Life"},
)


def daily_stoic_quote(on_date: date | None = None) -> StoicQuote:
    day = on_date or date.today()
    digest = hashlib.sha256(day.isoformat().encode("utf-8")).hexdigest()
    index = int(digest[:8], 16) % len(_QUOTES)
    return _QUOTES[index]
