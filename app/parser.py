import re
from typing import Optional
from datetime import datetime
from app.models import Promotion


# Patterns for each field
PATTERNS = {
    "destination":       re.compile(r"DESTINO:\s*(.+)", re.IGNORECASE),
    "origin":            re.compile(r"Origem:\s*(.+?)\s*\((\w{3})\)", re.IGNORECASE),
    "dest_full":         re.compile(r"Destino:\s*(.+?)\s*\((\w{3})\)", re.IGNORECASE),
    "airline":           re.compile(r"Companhia:\s*(.+)", re.IGNORECASE),
    "program":           re.compile(r"Programa:\s*(.+)", re.IGNORECASE),
    "cabin":             re.compile(r"Classe:\s*(.+)", re.IGNORECASE),
    "miles":             re.compile(r"([\d.,]+)\s*MILHAS\s*POR\s*TRECHO", re.IGNORECASE),
    "outbound_header":   re.compile(r"Datas dispon[ií]veis de ida:", re.IGNORECASE),
    "return_header":     re.compile(r"Datas dispon[ií]veis volta:", re.IGNORECASE),
    "month_dates":       re.compile(r"([A-Za-záàâãéêíóôõúç]+/\d{4}):\s*([\d,\s]+)"),
}


def _parse_miles(raw: str) -> int:
    cleaned = raw.replace(".", "").replace(",", "")
    return int(cleaned)


def _parse_date_block(lines: list[str]) -> dict[str, list[int]]:
    result = {}
    for line in lines:
        m = PATTERNS["month_dates"].search(line)
        if m:
            month_key = m.group(1).strip()
            days = [int(d.strip()) for d in m.group(2).split(",") if d.strip().isdigit()]
            result[month_key] = days
    return result


def parse_message(text: str, message_id: int) -> Optional[Promotion]:
    """Parse a Telegram promotion message into a Promotion object."""
    try:
        lines = text.splitlines()

        destination = None
        origin_city = origin_code = None
        destination_city = destination_code = None
        airline = program = cabin_class = None
        miles_per_segment = None
        outbound_dates: dict[str, list[int]] = {}
        return_dates: dict[str, list[int]] = {}

        # State machine to collect date blocks
        state = None  # None | "outbound" | "return"
        outbound_lines: list[str] = []
        return_lines: list[str] = []

        for line in lines:
            stripped = line.strip()

            # Destination header
            m = PATTERNS["destination"].search(stripped)
            if m and destination is None:
                destination = m.group(1).strip()
                continue

            # Origin
            m = PATTERNS["origin"].search(stripped)
            if m and origin_city is None:
                origin_city = m.group(1).strip()
                origin_code = m.group(2).upper()
                continue

            # Destination city/code (the "Destino:" line inside the body)
            m = PATTERNS["dest_full"].search(stripped)
            if m and destination_city is None:
                destination_city = m.group(1).strip()
                destination_code = m.group(2).upper()
                continue

            # Airline
            m = PATTERNS["airline"].search(stripped)
            if m:
                airline = m.group(1).strip()
                continue

            # Program
            m = PATTERNS["program"].search(stripped)
            if m:
                program = m.group(1).strip()
                continue

            # Cabin class
            m = PATTERNS["cabin"].search(stripped)
            if m:
                cabin_class = m.group(1).strip()
                continue

            # Miles
            m = PATTERNS["miles"].search(stripped)
            if m:
                miles_per_segment = _parse_miles(m.group(1))
                continue

            # Outbound dates header
            if PATTERNS["outbound_header"].search(stripped):
                state = "outbound"
                continue

            # Return dates header
            if PATTERNS["return_header"].search(stripped):
                state = "return"
                continue

            # Collect date lines
            if state == "outbound" and PATTERNS["month_dates"].search(stripped):
                outbound_lines.append(stripped)
            elif state == "return" and PATTERNS["month_dates"].search(stripped):
                return_lines.append(stripped)
            elif state is not None and stripped and not PATTERNS["month_dates"].search(stripped):
                # Stop collecting when a non-date line appears (e.g. warning text)
                if not stripped.startswith("⚠️") and not stripped.startswith("--"):
                    pass  # allow blank lines
                else:
                    state = None

        outbound_dates = _parse_date_block(outbound_lines)
        return_dates = _parse_date_block(return_lines)

        # Require the essential fields
        if not all([destination, origin_city, destination_city, airline, program, cabin_class, miles_per_segment]):
            return None

        return Promotion(
            message_id=message_id,
            destination=destination,
            origin_city=origin_city,
            origin_code=origin_code,
            destination_city=destination_city,
            destination_code=destination_code,
            airline=airline,
            program=program,
            cabin_class=cabin_class,
            miles_per_segment=miles_per_segment,
            outbound_dates=outbound_dates,
            return_dates=return_dates,
            raw_text=text,
            collected_at=datetime.utcnow(),
        )
    except Exception:
        return None
