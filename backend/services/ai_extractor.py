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

    Uses Google Gemini API when GEMINI_API_KEY is set, otherwise falls back
    to regex-based extraction.

    Args:
        text: Raw text extracted from a PDF.

    Returns:
        Dict with keys: customer_name (str), line_items (list of dicts)
    """
    api_key = os.getenv("GEMINI_API_KEY")

    if api_key and api_key != "your-key-here":
        return await _extract_with_gemini(text, api_key)
    else:
        logger.info("No GEMINI_API_KEY set, using fallback regex parser")
        return _extract_with_fallback(text)


async def _extract_with_gemini(text: str, api_key: str) -> Dict[str, Any]:
    """Extract data using Google Gemini API."""
    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")

        prompt = f"{SYSTEM_PROMPT}\n\nExtract data from this LPO:\n\n{text}"
        response = model.generate_content(prompt)

        content = response.text

        # Gemini sometimes wraps JSON in markdown code fences, strip them
        content = content.strip()
        if content.startswith("```json"):
            content = content[len("```json"):]
        elif content.startswith("```"):
            content = content[len("```"):]
        if content.endswith("```"):
            content = content[:-len("```")]
        content = content.strip()

        result = json.loads(content)

        return {
            "customer_name": result.get("customer_name", "Unknown"),
            "line_items": result.get("line_items", []),
        }
    except Exception as e:
        logger.error(f"Gemini extraction failed: {e}")
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


# Flexible unit pattern that matches all common unit variations case-insensitively
_UNIT_PATTERN = r"(?:crates?|bags?|bunches?|nets?|kgs?|kilograms?|boxes?|pieces?|dozens?)"


def _extract_line_items(text: str) -> List[Dict[str, Any]]:
    """Try to extract line items from LPO text using regex patterns.

    Processes each line individually, trying multiple patterns per line
    to handle PDFs that mix formats (e.g., some lines with separators,
    some without).
    """
    items = []

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

    # Pattern 1: quantity unit item_name (e.g., "5 Crates Tomatoes", "5kgs cabbages")
    pattern1 = r"^(\d+(?:\.\d+)?)\s*(" + _UNIT_PATTERN + r")\s+(.+?)$"
    # Pattern 2: item_name - quantity unit (e.g., "Tomatoes - 5 Crates", "cabbages - 5kgs")
    pattern2 = r"^([A-Za-z][A-Za-z ]*?)\s*[-:]\s*(\d+(?:\.\d+)?)\s*(" + _UNIT_PATTERN + r")\s*$"
    # Pattern 3: item_name quantity unit (e.g., "kitunguu 1 kg", "mangoes 1 bag")
    pattern3 = r"^([A-Za-z][A-Za-z ]*?)\s+(\d+(?:\.\d+)?)\s*(" + _UNIT_PATTERN + r")\s*$"
    # Pattern 4: table row "item_name | quantity | unit" or with tabs/multiple spaces
    pattern4 = r"^([A-Za-z][A-Za-z ]*?)(?:\t|\s{2,}|\|)\s*(\d+(?:\.\d+)?)\s*(?:\t|\s{2,}|\|)\s*(" + _UNIT_PATTERN + r")\s*$"

    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue

        matched = False

        # Try pattern 1: quantity unit item_name
        match = re.match(pattern1, line, re.IGNORECASE)
        if match:
            quantity = float(match.group(1))
            unit = _normalize_unit(match.group(2).strip())
            item_name = match.group(3).strip()
            item_lower = item_name.lower()
            if item_lower in swahili_map:
                item_name = swahili_map[item_lower]
            items.append({"item_name": item_name, "quantity": quantity, "unit": unit})
            matched = True

        # Try pattern 2: item_name - quantity unit
        if not matched:
            match = re.match(pattern2, line, re.IGNORECASE)
            if match:
                item_name = match.group(1).strip()
                quantity = float(match.group(2))
                unit = _normalize_unit(match.group(3).strip())
                item_lower = item_name.lower()
                if item_lower in swahili_map:
                    item_name = swahili_map[item_lower]
                items.append({"item_name": item_name, "quantity": quantity, "unit": unit})
                matched = True

        # Try pattern 3: item_name quantity unit
        if not matched:
            match = re.match(pattern3, line, re.IGNORECASE)
            if match:
                item_name = match.group(1).strip()
                quantity = float(match.group(2))
                unit = _normalize_unit(match.group(3).strip())
                item_lower = item_name.lower()
                if item_lower in swahili_map:
                    item_name = swahili_map[item_lower]
                if item_name and len(item_name) > 1:
                    items.append({"item_name": item_name, "quantity": quantity, "unit": unit})
                    matched = True

        # Try pattern 4: table row style
        if not matched:
            match = re.match(pattern4, line, re.IGNORECASE)
            if match:
                item_name = match.group(1).strip()
                quantity = float(match.group(2))
                unit = _normalize_unit(match.group(3).strip())
                item_lower = item_name.lower()
                if item_lower in swahili_map:
                    item_name = swahili_map[item_lower]
                if item_name and len(item_name) > 1:
                    items.append({"item_name": item_name, "quantity": quantity, "unit": unit})

    return items
