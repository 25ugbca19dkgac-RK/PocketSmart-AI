"""
gemini_utils.py – PocketSmart AI Recommendation Engine
Handles prompt orchestration, budget formatting, domain segmentation,
and image analysis for multimodal tasks using Gemini.
"""

import os
import base64
from google import genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = "gemini-3.6-flash"


def get_client():
    """Return configured Gemini client."""
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY not found in environment variables.")
    return genai.Client(api_key=GEMINI_API_KEY)


# ─────────────── Platform link helpers ───────────────

PLATFORM_LINKS = {
    "amazon": "https://www.amazon.in/s?k=",
    "flipkart": "https://www.flipkart.com/search?q=",
    "ikea": "https://www.ikea.com/in/en/search/?q=",
    "swiggy": "https://www.swiggy.com/search?query=",
    "zomato": "https://www.zomato.com/search?q=",
    "oyo": "https://www.oyorooms.com/search?query=",
    "myntra": "https://www.myntra.com/search?q=",
    "tanishq": "https://www.tanishq.co.in/search?q=",
}


def generate_shopping_links(keywords: list[str], platforms: list[str]) -> list[dict]:
    """Generate search links for given keywords across platforms."""
    links = []
    for kw in keywords:
        for platform in platforms:
            base = PLATFORM_LINKS.get(platform.lower())
            if base:
                links.append({
                    "platform": platform.capitalize(),
                    "keyword": kw,
                    "url": f"{base}{kw.replace(' ', '+')}"
                })
    return links


# ─────────────── Home Interior Recommendations ───────────────

def get_home_recommendations(budget: float, rooms: list[dict], family_size: int, preferences: str) -> dict:
    """
    Generate home interior recommendations.
    rooms: list of dicts like {"room_type": "Living Room", "items": {"lights": 2, "fans": 1, ...}}
    """
    client = get_client()

    rooms_description = ""
    all_keywords = []
    for room in rooms:
        items_str = ", ".join(f"{v} {k}" for k, v in room.get("items", {}).items() if v > 0)
        rooms_description += f"\n- {room['room_type']}: {items_str}"
        all_keywords.extend(
            [f"{room['room_type']} {k}" for k, v in room.get("items", {}).items() if v > 0]
        )

    prompt = f"""Act as a professional Home Interior and Budget Planning Expert.

Budget: ₹{budget:,.0f}
Family Size: {family_size}
Style Preferences: {preferences}
Rooms & Items Required:{rooms_description}

Please provide:
1. **Budget Allocation** – Break down the total budget across room categories proportionally.
2. **Product Recommendations** – For EACH item in each room, suggest 2-3 specific products with:
   - Product name
   - Estimated price (in ₹)
   - Platform (Amazon / Flipkart / IKEA)
   - Why it's a good fit
3. **Design Tips** – 2-3 practical interior design tips for the overall space.
4. **Budget Summary** – Total estimated spend vs. available budget, with savings if any.

Format the response in clean markdown with headers and bullet points."""

    response = client.models.generate_content(model=MODEL_NAME, contents=prompt)

    shopping_links = generate_shopping_links(
        all_keywords[:10],
        ["amazon", "flipkart", "ikea"]
    )

    return {
        "status": "success",
        "budget": budget,
        "ai_recommendation": response.text,
        "shopping_links": shopping_links,
        "category": "home"
    }


# ─────────────── Party Planner Recommendations ───────────────

def get_party_recommendations(
    event_type: str,
    budget: float,
    guest_count: int,
    venue_details: str,
    food_preference: str = "mixed",
    theme: str = "",
) -> dict:
    """Generate party planning recommendations."""
    client = get_client()

    # Budget proportional allocation based on event type
    if event_type.lower() in ["wedding", "engagement", "reception"]:
        allocation = {"catering": 40, "venue": 25, "decoration": 20, "entertainment": 15}
    elif event_type.lower() in ["birthday", "anniversary"]:
        allocation = {"catering": 35, "decoration": 25, "entertainment": 25, "venue": 15}
    elif event_type.lower() in ["corporate", "conference", "seminar"]:
        allocation = {"venue": 30, "catering": 30, "technology": 25, "decoration": 15}
    else:
        allocation = {"catering": 30, "venue": 25, "decoration": 25, "entertainment": 20}

    alloc_str = "\n".join(
        f"  - {cat.capitalize()}: ₹{budget * pct / 100:,.0f} ({pct}%)"
        for cat, pct in allocation.items()
    )

    prompt = f"""Act as a professional Event Planning and Budgeting Expert.

Event Type: {event_type}
Total Budget: ₹{budget:,.0f}
Guest Count: {guest_count}
Venue Context: {venue_details}
Food Preference: {food_preference}
Theme: {theme or "No specific theme"}

Suggested Budget Allocation:
{alloc_str}

Please provide:
1. **Venue Suggestions** – 2-3 venue options (referencing OYO, local banquet halls) with estimated cost.
2. **Catering Plan** – Menu suggestions with per-plate cost, sourcing from Swiggy/Zomato where applicable.
3. **Decoration Ideas** – Theme-appropriate decoration items with sources (Amazon/Flipkart).
4. **Entertainment** – Music, games, or activity suggestions within budget.
5. **Complete Budget Breakdown** – Table showing each category's allocated vs estimated spend.
6. **Pro Tips** – 3 money-saving tips for this type of event.

Format in clean markdown with headers, tables, and bullet points."""

    response = client.models.generate_content(model=MODEL_NAME, contents=prompt)

    keywords = [
        f"{event_type} decoration",
        f"{event_type} party supplies",
        f"{food_preference} catering",
        f"{theme} party theme" if theme else f"{event_type} theme"
    ]
    shopping_links = generate_shopping_links(
        keywords,
        ["amazon", "flipkart", "swiggy", "zomato", "oyo"]
    )

    return {
        "status": "success",
        "event_type": event_type,
        "budget": budget,
        "allocation": allocation,
        "ai_recommendation": response.text,
        "shopping_links": shopping_links,
        "category": "party"
    }


# ─────────────── Jewelry Recommendations ───────────────

def get_jewelry_recommendations(
    budget: float,
    occasion: str,
    style_preference: str,
    metal_preference: str = "gold",
    image_data: bytes | None = None,
    image_mime: str = "image/jpeg",
) -> dict:
    """Generate jewelry recommendations, optionally analyzing an outfit image."""
    client = get_client()

    image_analysis = ""
    contents = []

    if image_data:
        # Multimodal: analyze outfit image first
        encoded = base64.standard_b64encode(image_data).decode("utf-8")
        contents = [
            {
                "parts": [
                    {"text": (
                        "Analyze this outfit image. Identify the dominant colors, fabric style, "
                        "neckline type, and overall aesthetic. Then suggest what types of jewelry "
                        "(necklace, earrings, bangles, rings) would complement this outfit for a "
                        f"{occasion}. Budget is ₹{budget:,.0f}. "
                        f"Style preference: {style_preference}. Metal preference: {metal_preference}."
                    )},
                    {"inline_data": {"mime_type": image_mime, "data": encoded}}
                ]
            }
        ]
    else:
        prompt = f"""Act as a professional Jewelry Stylist and Budget Advisor.

Budget: ₹{budget:,.0f}
Occasion: {occasion}
Style Preference: {style_preference}
Metal Preference: {metal_preference}

Please provide:
1. **Jewelry Set Recommendations** – Suggest 3 complete jewelry sets (necklace + earrings + bangles/bracelet) with:
   - Design description
   - Estimated price for each piece
   - Platform (Amazon / Flipkart / Tanishq / Myntra)
   - Occasion suitability
2. **Color Coordination Tips** – What colors/outfits pair well with each set.
3. **Budget Breakdown** – How the budget is distributed across pieces.
4. **Care Tips** – How to maintain the suggested jewelry.

Format in clean markdown with headers and bullet points."""
        contents = prompt

    response = client.models.generate_content(model=MODEL_NAME, contents=contents)

    keywords = [
        f"{occasion} jewelry",
        f"{style_preference} {metal_preference} jewelry",
        f"{metal_preference} necklace set",
        f"{occasion} earrings"
    ]
    shopping_links = generate_shopping_links(
        keywords,
        ["amazon", "flipkart", "myntra", "tanishq"]
    )

    return {
        "status": "success",
        "budget": budget,
        "occasion": occasion,
        "ai_recommendation": response.text,
        "shopping_links": shopping_links,
        "category": "jewelry"
    }
