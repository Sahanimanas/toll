"""OCR engines plus plate-text normalization and regional validation.

Normalization fixes the classic confusion pairs (O<->0, I<->1, S<->5, B<->8)
using positional expectations from the region's plate grammar, then validates
against the region pattern. Validation failures are rejected before ingest.
"""

import logging
import re

import numpy as np

logger = logging.getLogger(__name__)

# Region grammars. Each entry: full-match regexes for valid plates.
REGION_PATTERNS: dict[str, list[re.Pattern]] = {
    # India: MH12AB1234 / MH12A1234 / DL1CAB1234 (simplified), BH series 22BH1234AB
    "IN": [
        re.compile(r"^[A-Z]{2}\d{1,2}[A-Z]{1,3}\d{4}$"),
        re.compile(r"^\d{2}BH\d{4}[A-Z]{1,2}$"),
    ],
    # EU-ish generic
    "EU": [re.compile(r"^[A-Z]{1,3}\d{1,4}[A-Z]{0,3}$")],
    # Generic fallback: 5-12 alphanumerics
    "GENERIC": [re.compile(r"^[A-Z0-9]{5,12}$")],
}

_LETTER_TO_DIGIT = {"O": "0", "Q": "0", "I": "1", "L": "1", "Z": "2", "S": "5", "B": "8", "G": "6", "T": "7"}
_DIGIT_TO_LETTER = {v: k for k, v in {"O": "0", "I": "1", "S": "5", "B": "8", "G": "6", "Z": "2"}.items()}

# Registered state/UT codes; used to reject look-alike windows during
# embedded-plate extraction (e.g. 'BO4C3337' carved out of 'WB04C3337').
_IN_STATE_CODES = frozenset(
    "AN AP AR AS BR CH CG CT DD DL DN GA GJ HP HR JH JK KA KL LA LD MH ML MN "
    "MP MZ NL OD OR PB PY RJ SK TN TR TS TG UK UA UP WB".split()
)


def clean_text(raw: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", raw.upper())


def _coerce_indian(text: str) -> str:
    """Coerce characters into India's LLDDLLDDDD-style positional grammar."""
    if not (8 <= len(text) <= 11):
        return text
    chars = list(text)
    # First two: letters (state code)
    for i in range(2):
        chars[i] = _DIGIT_TO_LETTER.get(chars[i], chars[i])
    # Next two: digits (RTO code)
    for i in range(2, min(4, len(chars))):
        chars[i] = _LETTER_TO_DIGIT.get(chars[i], chars[i])
    # Last four: digits
    for i in range(len(chars) - 4, len(chars)):
        chars[i] = _LETTER_TO_DIGIT.get(chars[i], chars[i])
    # Middle: letters (series)
    for i in range(4, len(chars) - 4):
        chars[i] = _DIGIT_TO_LETTER.get(chars[i], chars[i])
    return "".join(chars)


def _extract_embedded(text: str, region: str) -> str | None:
    """Salvage a valid plate embedded in a longer OCR read.

    OCR frequently glues surrounding plate furniture onto the number — the
    IND country tag, state names, dealer text — e.g. 'INDKA19P8488'. Slide a
    window over the string and return the best valid candidate: fewest
    coerced characters first (a nearly-literal match beats one manufactured
    by confusion-pair rewrites), then longest (a full plate beats its own
    valid suffix), then leftmost.
    """
    best: tuple[tuple[int, int, int], str] | None = None
    for length in range(11, 7, -1):
        for start in range(0, len(text) - length + 1):
            window = text[start : start + length]
            candidate = _coerce_indian(window) if region == "IN" else window
            if not validate_plate(candidate, region):
                continue
            changes = sum(a != b for a, b in zip(window, candidate))
            key = (changes, -length, start)
            if best is None or key < best[0]:
                best = (key, candidate)
    return best[1] if best else None


def normalize_plate(raw: str, region: str = "IN") -> str:
    text = clean_text(raw)
    if region == "IN":
        coerced = _coerce_indian(text)
        if validate_plate(coerced, region):
            return coerced
    if not validate_plate(text, region):
        embedded = _extract_embedded(text, region)
        if embedded:
            return embedded
    return text


def validate_plate(text: str, region: str = "IN") -> bool:
    # Strict regional grammar when the region is known; generic shape otherwise.
    patterns = REGION_PATTERNS.get(region) or REGION_PATTERNS["GENERIC"]
    if not any(p.fullmatch(text) for p in patterns):
        return False
    # Grammar-shaped junk (e.g. an OSD timestamp coerced to 'OI09Z8245')
    # still fails unless it starts with a registered state code or BH series.
    if region == "IN" and text[2:4] != "BH" and text[:2] not in _IN_STATE_CODES:
        return False
    return True


def _reading_order(results: list) -> list:
    """Order OCR boxes line by line (top-to-bottom), left-to-right within a
    line. A pure x sort interleaves the rows of two-line plates."""
    if not results:
        return results
    heights = [abs(box[2][1] - box[0][1]) for box, _, _ in results]
    line_height = max(float(np.median(heights)), 1.0)

    def key(result):
        box = result[0]
        y_center = (box[0][1] + box[2][1]) / 2.0
        return (int(y_center // line_height), box[0][0])

    return sorted(results, key=key)


class EasyOcrEngine:
    def __init__(self, device: str = "cpu"):
        import easyocr

        self.reader = easyocr.Reader(["en"], gpu=device.startswith("cuda"))

    def read(self, plate_gray: np.ndarray) -> tuple[str, float]:
        results = self.reader.readtext(plate_gray, detail=1, paragraph=False)
        if not results:
            return "", 0.0
        text = "".join(r[1] for r in _reading_order(results))
        confidence = float(np.mean([r[2] for r in results]))
        return text, confidence


class TesseractEngine:
    def __init__(self):
        import pytesseract

        pytesseract.get_tesseract_version()  # raises if binary missing
        self.pytesseract = pytesseract

    def read(self, plate_gray: np.ndarray) -> tuple[str, float]:
        config = "--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        data = self.pytesseract.image_to_data(
            plate_gray, config=config, output_type=self.pytesseract.Output.DICT
        )
        words, confs = [], []
        for word, conf in zip(data["text"], data["conf"]):
            conf = float(conf)
            if word.strip() and conf > 0:
                words.append(word.strip())
                confs.append(conf)
        if not words:
            return "", 0.0
        return "".join(words), float(np.mean(confs)) / 100.0


def build_ocr_engine(kind: str, device: str = "cpu"):
    if kind in ("auto", "easyocr"):
        try:
            engine = EasyOcrEngine(device)
            logger.info("OCR engine: EasyOCR on %s", device)
            return engine
        except Exception as exc:
            if kind == "easyocr":
                raise
            logger.warning("EasyOCR unavailable (%s); trying Tesseract", exc)
    if kind in ("auto", "tesseract"):
        try:
            engine = TesseractEngine()
            logger.info("OCR engine: Tesseract")
            return engine
        except Exception as exc:
            if kind == "tesseract":
                raise
            logger.error("No OCR engine available (%s); recognitions disabled", exc)
    return None
