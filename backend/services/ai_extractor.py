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


def _extract_multiline_table_items(text: str) -> List[Dict[str, Any]]:
    """Extract items from multi-line table format produced by pymupdf.

    pymupdf often extracts PDF table cells as separate lines:
        1
        Tomatoes
        5
        Crates
        1500
        7500

    This function detects such sequences and reassembles them into items.
    Each table row has fields: row_number, item_name, quantity, unit,
    and optionally unit_price and total.
    Item names may span multiple lines (e.g., "Sukuma Wiki").
    """
    lines = [line.strip() for line in text.split("\n")]
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

    unit_re = re.compile(r"^" + _UNIT_PATTERN + r"$", re.IGNORECASE)

    # Find the table header to locate where data starts.
    # Look for a line that is "#" or "Item Description" which indicates a table header.
    header_found = False
    i = 0
    while i < len(lines):
        if lines[i] == "#" or lines[i].lower() == "item description":
            header_found = True
            break
        i += 1

    if not header_found:
        return []

    # Skip all header lines until we reach the first row number "1"
    while i < len(lines):
        if lines[i] == "1":
            break
        i += 1

    if i >= len(lines):
        return []

    # Parse table rows. Strategy: look for a row number, then scan forward
    # for a unit line. Everything between row_number and the first numeric
    # line before the unit is the item name; the numeric line just before
    # the unit is the quantity.
    expected_row = 1
    while i < len(lines):
        line = lines[i]

        # Must match the expected row number exactly
        if line != str(expected_row):
            # If we hit non-row content, the table has ended
            if re.match(r"^(GRAND|Authorized|Terms)", line, re.IGNORECASE):
                break
            i += 1
            continue

        # Found row number; advance past it
        i += 1

        # Collect all lines until we find a unit line.
        # The structure is: [item_name lines...] [quantity] [unit] [price numbers...]
        # We scan forward to find the unit, then work backwards.
        scan = i
        unit_idx = None
        while scan < len(lines):
            if unit_re.match(lines[scan]):
                unit_idx = scan
                break
            # Stop scanning if we hit end-of-table markers
            if re.match(r"^(GRAND|Authorized|Terms)", lines[scan], re.IGNORECASE):
                break
            scan += 1

        if unit_idx is None:
            break

        # The line just before the unit is the quantity
        qty_idx = unit_idx - 1
        if qty_idx < i:
            i = scan + 1
            expected_row += 1
            continue

        if not re.match(r"^\d+(?:\.\d+)?$", lines[qty_idx]):
            i = scan + 1
            expected_row += 1
            continue

        quantity = float(lines[qty_idx])
        unit = _normalize_unit(lines[unit_idx])

        # Everything between i and qty_idx is the item name
        item_parts = lines[i:qty_idx]
        item_name = " ".join(item_parts).strip()

        # Advance past unit and skip up to 2 trailing numeric fields (unit_price, total)
        i = unit_idx + 1
        skipped = 0
        while i < len(lines) and skipped < 2 and re.match(r"^[\d,]+(?:\.\d+)?$", lines[i]):
            i += 1
            skipped += 1

        # Apply Swahili mapping
        item_lower = item_name.lower()
        if item_lower in swahili_map:
            item_name = swahili_map[item_lower]

        if item_name and len(item_name) > 1:
            items.append({"item_name": item_name, "quantity": quantity, "unit": unit})

        expected_row += 1

    return items


def _extract_line_items(text: str) -> List[Dict[str, Any]]:
    """Try to extract line items from LPO text using regex patterns.

    First attempts multi-line table extraction (for pymupdf output where each
    cell is on its own line), then falls back to per-line pattern matching.
    """
    # Try multi-line table extraction first (handles pymupdf output)
    items = _extract_multiline_table_items(text)
    if items:
        return items

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

    # Pattern 0 (LPO table): row number glued to item name, then quantity, unit,
    # with optional trailing price columns ignored.
    # Matches: "1Tomatoes 5 Crates 1500 7500" or "3Sukuma Wiki 3 Bunches 200 600"
    pattern0 = (
        r"^\d+([A-Za-z][A-Za-z ]*?)\s+(\d+(?:\.\d+)?)\s+("
        + _UNIT_PATTERN
        + r")(?:\s+\d[\d,]*(?:\.\d+)?)*\s*$"
    )
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

        # Try pattern 0: LPO table row (row_number glued to item name)
        match = re.match(pattern0, line, re.IGNORECASE)
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

        # Try pattern 1: quantity unit item_name
        if not matched:
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
