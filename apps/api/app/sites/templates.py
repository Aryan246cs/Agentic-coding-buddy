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
    "agency": {"name": "Creative Agency", "blurb": "A bold studio introduction with services, selected clients, and a project enquiry.", "best_for": ["agency", "branding", "creative studio", "marketing", "design studio"], "wants_images": True},
    "restaurant": {"name": "Restaurant & Café", "blurb": "A warm home for your menu, opening hours, location, and reservations.", "best_for": ["restaurant", "cafe", "café", "bakery", "dining", "menu"], "wants_images": True},
    "wellness": {"name": "Wellness & Spa", "blurb": "A calm, welcoming page for treatments, practitioners, and appointments.", "best_for": ["wellness", "spa", "meditation", "therapy", "yoga", "mindfulness"], "wants_images": True},
    "saas": {"name": "Software Product", "blurb": "Explain the product, show its value, and guide visitors to a demo or sign-up.", "best_for": ["software", "saas", "platform", "startup", "technology", "app"], "wants_images": False},
    "product": {"name": "Product Launch", "blurb": "A focused product story with benefits, details, and a clear buying action.", "best_for": ["product launch", "product", "shop", "ecommerce", "e-commerce"], "wants_images": True},
    "course": {"name": "Online Course", "blurb": "Present what students will learn, who teaches it, and how to enroll.", "best_for": ["course", "class", "curriculum", "learn", "education", "instructor"], "wants_images": True},
    "newsletter": {"name": "Newsletter", "blurb": "Introduce your publication, sample the latest issue, and invite subscriptions.", "best_for": ["newsletter", "publication", "substack", "journal", "writing"], "wants_images": False},
    "podcast": {"name": "Podcast", "blurb": "Feature the show, recent episodes, hosts, and where to listen.", "best_for": ["podcast", "episodes", "show", "host", "audio"], "wants_images": True},
    "wedding": {"name": "Wedding & Celebration", "blurb": "Share the date, story, schedule, venue, and RSVP details.", "best_for": ["wedding", "celebration", "anniversary", "ceremony", "rsvp"], "wants_images": True},
    "nonprofit": {"name": "Nonprofit & Community", "blurb": "Make your mission clear and help people support or join your work.", "best_for": ["nonprofit", "non-profit", "charity", "foundation", "community", "cause"], "wants_images": True},
    "real_estate": {"name": "Real Estate", "blurb": "Showcase properties, neighborhood knowledge, and a simple way to enquire.", "best_for": ["real estate", "property", "realtor", "broker", "homes", "rentals"], "wants_images": True},
    "hospitality": {"name": "Stay & Hospitality", "blurb": "Set the scene for your stay with rooms, amenities, location, and booking details.", "best_for": ["hotel", "homestay", "hospitality", "resort", "guesthouse", "accommodation"], "wants_images": True},
    "fitness": {"name": "Fitness & Coaching", "blurb": "Introduce your approach, programs, coaches, schedule, and first session.", "best_for": ["fitness", "gym", "personal trainer", "training", "sports", "coach"], "wants_images": True},
    "resume": {"name": "Resume & Profile", "blurb": "A clear professional introduction with experience, skills, and contact links.", "best_for": ["resume", "cv", "career", "job seeker", "professional profile"], "wants_images": False},
    "creator": {"name": "Creator & Artist", "blurb": "Put your latest work, channels, and collaborations in one vivid place.", "best_for": ["creator", "influencer", "artist", "streamer", "youtube", "social"], "wants_images": True},
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
