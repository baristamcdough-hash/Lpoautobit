import json
import logging
import os
import re
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a data extraction assistant specialized in Kenyan Local Purchase Orders (LPOs) for fresh produce.

Extract the following from the provided LPO text:
1. customer_name: The name of the customer/business placing the order
2. line_items: A list of items ordered, each with:
   - item_name: Name of the produce item (standardize to English)
   - quantity: Numeric quantity ordered
   - unit: Unit of measurement (Crates, Bags, Bunches, Nets, Kg, etc.)

Common Kenyan produce name mappings (Swahili to English):
- Nyanya = Tomatoes
- Viazi = Potatoes
- Kitunguu = Onions
- Sukuma Wiki = Kale
- Mahindi = Maize/Corn
- Ndizi = Bananas
- Karoti = Carrots
- Pilipili = Peppers
- Kabichi = Cabbage
- Spinachi = Spinach

Return ONLY valid JSON in this exact format:
{
  "customer_name": "string",
  "line_items": [
    {"item_name": "string", "quantity": number, "unit": "string"}
  ]
}"""


async def extract_lpo_data(text: str) -> Dict[str, Any]:
    """Extract structured LPO data from raw text.

    Uses OpenAI API when OPENAI_API_KEY is set, otherwise falls back
    to regex-based extraction.

    Args:
        text: Raw text extracted from a PDF.

    Returns:
        Dict with keys: customer_name (str), line_items (list of dicts)
    """
    api_key = os.getenv("OPENAI_API_KEY")

    if api_key and api_key != "your-key-here":
        return await _extract_with_openai(text, api_key)
    else:
        logger.info("No OPENAI_API_KEY set, using fallback regex parser")
        return _extract_with_fallback(text)


async def _extract_with_openai(text: str, api_key: str) -> Dict[str, Any]:
    """Extract data using OpenAI API."""
    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=api_key)

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Extract data from this LPO:\n\n{text}"},
            ],
            temperature=0.0,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        result = json.loads(content)

        # Normalize item names for consistent aggregation across PDFs
        line_items = result.get("line_items", [])
        for item in line_items:
            if "item_name" in item:
                item["item_name"] = _normalize_item_name(item["item_name"])
            if "unit" in item:
                item["unit"] = _normalize_unit(item["unit"])

        return {
            "customer_name": result.get("customer_name", "Unknown"),
            "line_items": line_items,
        }
    except Exception as e:
        logger.error(f"OpenAI extraction failed: {e}")
        return _extract_with_fallback(text)


def _extract_with_fallback(text: str) -> Dict[str, Any]:
    """Fallback regex-based parser for extracting LPO data.

    Handles common LPO formats without requiring an API key.
    """
    customer_name = _extract_customer_name(text)
    line_items = _extract_line_items(text)

    return {
        "customer_name": customer_name,
        "line_items": line_items,
    }


def _extract_customer_name(text: str) -> str:
    """Try to extract customer name from LPO text."""
    # Common patterns: "Customer: X", "To: X", "Bill To: X", "Client: X"
    patterns = [
        r"(?:Customer|Client|Bill\s*To|Ship\s*To|To)\s*:\s*(.+?)(?:\n|$)",
        r"(?:FROM|From)\s*:\s*(.+?)(?:\n|$)",
        r"(?:LPO|LOCAL PURCHASE ORDER)\s*[-:]?\s*\n\s*(.+?)(?:\n|$)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            if name and len(name) > 2:
                return name

    # Try to find a business name (capitalized words that look like a name)
    lines = text.strip().split("\n")
    for line in lines[:10]:
        line = line.strip()
        if line and len(line) > 3 and not line.startswith("Date"):
            # Check if line looks like a name (mostly alphabetic)
            if re.match(r"^[A-Za-z\s&\'-]+$", line) and len(line) < 60:
                return line

    return "Unknown Customer"


def _normalize_item_name(name: str) -> str:
    """Normalize produce item names to a canonical form.

    Handles plural/singular variations, common misspellings, and Swahili names
    so that the same item from different PDFs always gets the same name in the DB.
    This ensures proper consolidation when aggregating across multiple LPOs.
    """
    name = name.strip()
    if not name:
        return name

    # Swahili to English mapping
    swahili_map = {
        "nyanya": "Tomatoes",
        "viazi": "Potatoes",
        "kitunguu": "Onions",
        "sukuma wiki": "Kale",
        "sukuma": "Kale",
        "mahindi": "Maize",
        "ndizi": "Bananas",
        "karoti": "Carrots",
        "pilipili": "Peppers",
        "kabichi": "Cabbage",
        "spinachi": "Spinach",
    }

    name_lower = name.lower().strip()

    # Check Swahili mapping first
    if name_lower in swahili_map:
        return swahili_map[name_lower]

    # Canonical English produce names (maps variations to standard plural form)
    canonical_map = {
        "tomato": "Tomatoes",
        "tomatoes": "Tomatoes",
        "potato": "Potatoes",
        "potatoes": "Potatoes",
        "onion": "Onions",
        "onions": "Onions",
        "carrot": "Carrots",
        "carrots": "Carrots",
        "cabbage": "Cabbage",
        "cabbages": "Cabbage",
        "kale": "Kale",
        "spinach": "Spinach",
        "banana": "Bananas",
        "bananas": "Bananas",
        "pepper": "Peppers",
        "peppers": "Peppers",
        "maize": "Maize",
        "corn": "Maize",
        "sukuma wiki": "Kale",
        "watermelon": "Watermelon",
        "watermelons": "Watermelon",
        "mango": "Mangoes",
        "mangoes": "Mangoes",
        "mangos": "Mangoes",
        "avocado": "Avocados",
        "avocados": "Avocados",
        "pineapple": "Pineapples",
        "pineapples": "Pineapples",
        "orange": "Oranges",
        "oranges": "Oranges",
        "lemon": "Lemons",
        "lemons": "Lemons",
        "lime": "Limes",
        "limes": "Limes",
        "garlic": "Garlic",
        "ginger": "Ginger",
        "cucumber": "Cucumbers",
        "cucumbers": "Cucumbers",
        "lettuce": "Lettuce",
        "broccoli": "Broccoli",
        "peas": "Peas",
        "beans": "Beans",
        "bean": "Beans",
        "mushroom": "Mushrooms",
        "mushrooms": "Mushrooms",
        "courgette": "Courgettes",
        "courgettes": "Courgettes",
        "zucchini": "Courgettes",
    }

    if name_lower in canonical_map:
        return canonical_map[name_lower]

    # Default: return title-cased version for consistency
    return name.title()


def _normalize_unit(unit: str) -> str:
    """Normalize extracted units to their canonical form.

    Handles variations like 'kgs' -> 'Kg', 'bag' -> 'Bags', 'crate' -> 'Crates'.
    """
    unit_lower = unit.lower().strip()
    unit_map = {
        "kg": "Kg",
        "kgs": "Kg",
        "kilogram": "Kg",
        "kilograms": "Kg",
        "crate": "Crates",
        "crates": "Crates",
        "bag": "Bags",
        "bags": "Bags",
        "bunch": "Bunches",
        "bunches": "Bunches",
        "net": "Nets",
        "nets": "Nets",
        "box": "Boxes",
        "boxes": "Boxes",
        "piece": "Pieces",
        "pieces": "Pieces",
        "dozen": "Dozen",
        "dozens": "Dozen",
    }
    return unit_map.get(unit_lower, unit.capitalize())


def _extract_line_items(text: str) -> List[Dict[str, Any]]:
    """Try to extract line items from LPO text using regex patterns."""
    items = []

    # Pattern: quantity unit item_name (e.g., "5 Crates Tomatoes")
    pattern1 = r"(\d+(?:\.\d+)?)\s+(Crates?|Bags?|Bunches?|Nets?|Kg|Boxes?|Pieces?|Dozen)\s+(.+?)(?:\n|$)"
    for match in re.finditer(pattern1, text, re.IGNORECASE):
        quantity = float(match.group(1))
        unit = _normalize_unit(match.group(2).strip())
        item_name = _normalize_item_name(match.group(3).strip())
        items.append({"item_name": item_name, "quantity": quantity, "unit": unit})

    if items:
        return items

    # Pattern: item_name - quantity unit (e.g., "Tomatoes - 5 Crates")
    pattern2 = r"([A-Za-z\s]+?)\s*[-:]\s*(\d+(?:\.\d+)?)\s*(Crates?|Bags?|Bunches?|Nets?|Kg|Boxes?|Pieces?|Dozen)"
    for match in re.finditer(pattern2, text, re.IGNORECASE):
        item_name = _normalize_item_name(match.group(1).strip())
        quantity = float(match.group(2))
        unit = _normalize_unit(match.group(3).strip())
        items.append({"item_name": item_name, "quantity": quantity, "unit": unit})

    if items:
        return items

    # Pattern: table row style "item_name | quantity | unit" or with tabs/multiple spaces
    pattern3 = r"([A-Za-z\s]+?)(?:\t|\s{2,}|\|)\s*(\d+(?:\.\d+)?)\s*(?:\t|\s{2,}|\|)\s*(Crates?|Bags?|Bunches?|Nets?|Kg|Boxes?|Pieces?|Dozen)"
    for match in re.finditer(pattern3, text, re.IGNORECASE):
        item_name = _normalize_item_name(match.group(1).strip())
        quantity = float(match.group(2))
        unit = _normalize_unit(match.group(3).strip())
        if item_name and len(item_name) > 1:
            items.append({"item_name": item_name, "quantity": quantity, "unit": unit})

    return items
