from anpr_pipeline.ocr import _reading_order, clean_text, normalize_plate, validate_plate


def test_clean_text_strips_noise():
    assert clean_text(" mh-12 ab·1234 ") == "MH12AB1234"


def test_validate_indian_plates():
    assert validate_plate("MH12AB1234", "IN")
    assert validate_plate("DL8CAF5031", "IN")
    assert validate_plate("22BH1234AB", "IN")
    assert not validate_plate("ABC", "IN")
    assert not validate_plate("", "IN")


def test_validate_rejects_unknown_state_code():
    # Grammar-shaped but 'OI' is not a registered state code (an OSD
    # timestamp like '01 09:28:45' coerces into exactly this shape).
    assert not validate_plate("OI09Z8245", "IN")
    assert not validate_plate("XY12AB1234", "IN")


def test_normalize_does_not_manufacture_plate_from_timestamp():
    assert normalize_plate("01 09:28:45", "IN") == "01092845"
    assert not validate_plate(normalize_plate("010928245", "IN"), "IN")


def test_normalize_fixes_confusion_pairs():
    # O->0 in RTO code and trailing digits, 1->I style errors in series.
    assert normalize_plate("MH1ZAB12O4", "IN") == "MH12AB1204"
    assert normalize_plate("MHI2AB1234", "IN") == "MH12AB1234"


def test_normalize_leaves_valid_plate_untouched():
    assert normalize_plate("KA05MN7788", "IN") == "KA05MN7788"


def test_generic_fallback_region():
    assert validate_plate("ABC1234", "XX")  # unknown region -> generic pattern
    assert not validate_plate("AB", "XX")


def test_normalize_extracts_plate_from_glued_ocr_text():
    # Country tag / state names read off the plate frame around the number.
    assert normalize_plate("INDKA19P8488", "IN") == "KA19P8488"
    assert normalize_plate("IND KL47F7878 91", "IN") == "KL47F7878"
    # Coercion applies inside the extracted window too (O -> 0 in RTO code).
    assert normalize_plate("MB5175398WBO4C3337", "IN") == "WB04C3337"


def test_normalize_extraction_prefers_longest_match():
    # The full 10-char plate must win over its own valid 9-char suffix.
    assert normalize_plate("XKA19EQ1316", "IN") == "KA19EQ1316"


def test_normalize_no_embedded_plate_returns_cleaned_text():
    assert normalize_plate("KERALA TAMILNADU", "IN") == "KERALATAMILNADU"


def _box(x, y, w=50, h=20):
    return [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]


def test_reading_order_two_line_plate():
    # Two-line plate: "KA19" over "EQ1316". A pure x sort would interleave.
    results = [
        (_box(x=10, y=40), "EQ", 0.9),
        (_box(x=30, y=5), "KA19", 0.9),
        (_box(x=70, y=40), "1316", 0.9),
    ]
    assert "".join(r[1] for r in _reading_order(results)) == "KA19EQ1316"


def test_reading_order_single_line_unchanged():
    results = [
        (_box(x=60, y=10), "8488", 0.9),
        (_box(x=10, y=12), "KA19P", 0.9),
    ]
    assert "".join(r[1] for r in _reading_order(results)) == "KA19P8488"
