"""Website templates and themes.

The backend owns the *list* — what a planner may choose and what the validator
accepts. The frontend owns the *look*, because that is where the markup lives.
Keeping the list here means the AI can never pick a template that does not
exist, and adding one is a change in two obvious places.
"""

from __future__ import annotations

from typing import Any

SITE_TEMPLATES: dict[str, dict[str, Any]] = {
    "portfolio": {
        "name": "Portfolio",
        "blurb": "For designers, photographers, writers — work first, words second.",
        "best_for": ["designer", "photographer", "artist", "writer", "developer"],
        "wants_images": True,
    },
    "freelancer": {
        "name": "Freelancer",
        "blurb": "Services, rates and a way to get in touch.",
        "best_for": ["consultant", "freelancer", "tutor", "coach", "trainer"],
        "wants_images": False,
    },
    "business": {
        "name": "Local Business",
        "blurb": "For a shop, clinic or studio. What you do, where you are, how to reach you.",
        "best_for": ["shop", "clinic", "salon", "restaurant", "studio", "gym"],
        "wants_images": True,
    },
    "event": {
        "name": "Event",
        "blurb": "One page for a workshop, launch or meetup.",
        "best_for": ["event", "workshop", "conference", "meetup", "launch"],
        "wants_images": True,
    },
    "personal": {
        "name": "Personal",
        "blurb": "A simple page about you, with links.",
        "best_for": ["student", "researcher", "personal", "resume", "cv"],
        "wants_images": False,
    },
}

#: Theme keys the frontend has palettes for. `slate` is the safe default.
SITE_THEMES: tuple[str, ...] = (
    "slate",
    "ink",
    "forest",
    "clay",
    "indigo",
    "sand",
)


def suggest_template(description: str) -> str:
    """Best template for a description, by keyword.

    Used as the offline fallback and as a sanity default when the planner
    picks something odd.
    """
    lowered = description.lower()
    best, best_score = "personal", 0

    for key, template in SITE_TEMPLATES.items():
        score = sum(1 for word in template["best_for"] if word in lowered)
        if score > best_score:
            best, best_score = key, score

    return best
