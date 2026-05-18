"""
Language registry for MedBridge Ukraine.

Designed for global refugee/displaced-population use: covers the major
displacement source/host languages plus a free-text "custom" option for
tribal, indigenous, or otherwise uncommon languages without ISO 639-1 codes.

A language entry has:
    code        — ISO 639-1 or BCP 47 tag (or "custom" for free-text)
    name_en     — English display name
    native      — native script display name (best-effort)
    region      — grouping label for the UI dropdown
    rtl         — right-to-left script
    flag        — emoji flag or symbol for the UI

`resolve_language()` is the single helper the rest of the codebase calls
to turn a (code, language_other) pair into a human-readable language name
suitable for AI prompts and PDF rendering.
"""

from __future__ import annotations

from typing import TypedDict


class LanguageEntry(TypedDict):
    code: str
    name_en: str
    native: str
    region: str
    rtl: bool
    flag: str


SUPPORTED_LANGUAGES: list[LanguageEntry] = [
    # ── Ukraine / Eastern Europe (original target population) ─────────
    {"code": "uk", "name_en": "Ukrainian", "native": "Українська", "region": "Ukraine & Eastern Europe", "rtl": False, "flag": "🇺🇦"},
    {"code": "ru", "name_en": "Russian",   "native": "Русский",    "region": "Ukraine & Eastern Europe", "rtl": False, "flag": "🇷🇺"},
    {"code": "pl", "name_en": "Polish",    "native": "Polski",     "region": "Ukraine & Eastern Europe", "rtl": False, "flag": "🇵🇱"},
    {"code": "ro", "name_en": "Romanian",  "native": "Română",     "region": "Ukraine & Eastern Europe", "rtl": False, "flag": "🇷🇴"},
    {"code": "hu", "name_en": "Hungarian", "native": "Magyar",     "region": "Ukraine & Eastern Europe", "rtl": False, "flag": "🇭🇺"},
    {"code": "sk", "name_en": "Slovak",    "native": "Slovenčina", "region": "Ukraine & Eastern Europe", "rtl": False, "flag": "🇸🇰"},
    {"code": "be", "name_en": "Belarusian","native": "Беларуская", "region": "Ukraine & Eastern Europe", "rtl": False, "flag": "🇧🇾"},
    {"code": "mo", "name_en": "Moldovan",  "native": "Moldovenească", "region": "Ukraine & Eastern Europe", "rtl": False, "flag": "🇲🇩"},

    # ── Middle East & North Africa ────────────────────────────────────
    {"code": "ar",     "name_en": "Arabic (Modern Standard)", "native": "العربية",     "region": "Middle East & North Africa", "rtl": True,  "flag": "🌍"},
    {"code": "ar-SY",  "name_en": "Arabic (Syrian)",          "native": "العربية السورية", "region": "Middle East & North Africa", "rtl": True,  "flag": "🇸🇾"},
    {"code": "ar-IQ",  "name_en": "Arabic (Iraqi)",           "native": "العربية العراقية", "region": "Middle East & North Africa", "rtl": True,  "flag": "🇮🇶"},
    {"code": "ar-PS",  "name_en": "Arabic (Palestinian)",     "native": "العربية الفلسطينية", "region": "Middle East & North Africa", "rtl": True,  "flag": "🇵🇸"},
    {"code": "ar-YE",  "name_en": "Arabic (Yemeni)",          "native": "العربية اليمنية", "region": "Middle East & North Africa", "rtl": True,  "flag": "🇾🇪"},
    {"code": "ku",     "name_en": "Kurdish (Kurmanji)",       "native": "Kurdî",          "region": "Middle East & North Africa", "rtl": False, "flag": "🌍"},
    {"code": "ckb",    "name_en": "Kurdish (Sorani)",         "native": "کوردیی ناوەندی",  "region": "Middle East & North Africa", "rtl": True,  "flag": "🌍"},
    {"code": "fa",     "name_en": "Persian / Farsi",          "native": "فارسی",          "region": "Middle East & North Africa", "rtl": True,  "flag": "🇮🇷"},
    {"code": "he",     "name_en": "Hebrew",                   "native": "עברית",          "region": "Middle East & North Africa", "rtl": True,  "flag": "🇮🇱"},
    {"code": "tr",     "name_en": "Turkish",                  "native": "Türkçe",         "region": "Middle East & North Africa", "rtl": False, "flag": "🇹🇷"},

    # ── Central & South Asia (Afghanistan, Pakistan, etc.) ────────────
    {"code": "ps",    "name_en": "Pashto",          "native": "پښتو",      "region": "Central & South Asia", "rtl": True,  "flag": "🇦🇫"},
    {"code": "fa-AF", "name_en": "Dari",            "native": "دری",       "region": "Central & South Asia", "rtl": True,  "flag": "🇦🇫"},
    {"code": "ur",    "name_en": "Urdu",            "native": "اردو",      "region": "Central & South Asia", "rtl": True,  "flag": "🇵🇰"},
    {"code": "uz",    "name_en": "Uzbek",           "native": "Oʻzbekcha", "region": "Central & South Asia", "rtl": False, "flag": "🇺🇿"},
    {"code": "tg",    "name_en": "Tajik",           "native": "Тоҷикӣ",    "region": "Central & South Asia", "rtl": False, "flag": "🇹🇯"},
    {"code": "hi",    "name_en": "Hindi",           "native": "हिन्दी",      "region": "Central & South Asia", "rtl": False, "flag": "🇮🇳"},
    {"code": "bn",    "name_en": "Bengali",         "native": "বাংলা",      "region": "Central & South Asia", "rtl": False, "flag": "🇧🇩"},
    {"code": "ta",    "name_en": "Tamil",           "native": "தமிழ்",      "region": "Central & South Asia", "rtl": False, "flag": "🇱🇰"},
    {"code": "si",    "name_en": "Sinhala",         "native": "සිංහල",      "region": "Central & South Asia", "rtl": False, "flag": "🇱🇰"},
    {"code": "ne",    "name_en": "Nepali",          "native": "नेपाली",      "region": "Central & South Asia", "rtl": False, "flag": "🇳🇵"},

    # ── Sub-Saharan Africa ────────────────────────────────────────────
    {"code": "sw", "name_en": "Swahili",   "native": "Kiswahili", "region": "Sub-Saharan Africa", "rtl": False, "flag": "🌍"},
    {"code": "so", "name_en": "Somali",    "native": "Soomaali",  "region": "Sub-Saharan Africa", "rtl": False, "flag": "🇸🇴"},
    {"code": "am", "name_en": "Amharic",   "native": "አማርኛ",      "region": "Sub-Saharan Africa", "rtl": False, "flag": "🇪🇹"},
    {"code": "ti", "name_en": "Tigrinya",  "native": "ትግርኛ",      "region": "Sub-Saharan Africa", "rtl": False, "flag": "🇪🇷"},
    {"code": "om", "name_en": "Oromo",     "native": "Afaan Oromoo","region": "Sub-Saharan Africa", "rtl": False, "flag": "🇪🇹"},
    {"code": "ha", "name_en": "Hausa",     "native": "Hausa",     "region": "Sub-Saharan Africa", "rtl": False, "flag": "🌍"},
    {"code": "yo", "name_en": "Yoruba",    "native": "Yorùbá",    "region": "Sub-Saharan Africa", "rtl": False, "flag": "🇳🇬"},
    {"code": "ig", "name_en": "Igbo",      "native": "Igbo",      "region": "Sub-Saharan Africa", "rtl": False, "flag": "🇳🇬"},
    {"code": "ln", "name_en": "Lingala",   "native": "Lingála",   "region": "Sub-Saharan Africa", "rtl": False, "flag": "🇨🇩"},
    {"code": "rw", "name_en": "Kinyarwanda","native": "Kinyarwanda","region": "Sub-Saharan Africa", "rtl": False, "flag": "🇷🇼"},

    # ── Southeast Asia & Myanmar ──────────────────────────────────────
    {"code": "my",  "name_en": "Burmese",                 "native": "မြန်မာစာ",   "region": "Southeast Asia", "rtl": False, "flag": "🇲🇲"},
    {"code": "rhg", "name_en": "Rohingya (Hanifi script)","native": "𐴌𐴗𐴥𐴝𐴙𐴚𐴒𐴙𐴝", "region": "Southeast Asia", "rtl": True,  "flag": "🌍"},
    {"code": "kar", "name_en": "Karen",                   "native": "ကညီ",     "region": "Southeast Asia", "rtl": False, "flag": "🌍"},
    {"code": "th",  "name_en": "Thai",                    "native": "ไทย",      "region": "Southeast Asia", "rtl": False, "flag": "🇹🇭"},
    {"code": "vi",  "name_en": "Vietnamese",              "native": "Tiếng Việt","region": "Southeast Asia", "rtl": False, "flag": "🇻🇳"},
    {"code": "tl",  "name_en": "Tagalog / Filipino",      "native": "Filipino", "region": "Southeast Asia", "rtl": False, "flag": "🇵🇭"},
    {"code": "id",  "name_en": "Indonesian",              "native": "Bahasa Indonesia", "region": "Southeast Asia", "rtl": False, "flag": "🇮🇩"},
    {"code": "ms",  "name_en": "Malay",                   "native": "Bahasa Melayu", "region": "Southeast Asia", "rtl": False, "flag": "🇲🇾"},
    {"code": "km",  "name_en": "Khmer",                   "native": "ខ្មែរ",       "region": "Southeast Asia", "rtl": False, "flag": "🇰🇭"},

    # ── Latin America / Indigenous Americas ───────────────────────────
    {"code": "es",  "name_en": "Spanish",        "native": "Español",      "region": "Latin America", "rtl": False, "flag": "🌎"},
    {"code": "pt",  "name_en": "Portuguese",     "native": "Português",    "region": "Latin America", "rtl": False, "flag": "🇧🇷"},
    {"code": "ht",  "name_en": "Haitian Creole", "native": "Kreyòl ayisyen","region": "Latin America", "rtl": False, "flag": "🇭🇹"},
    {"code": "qu",  "name_en": "Quechua",        "native": "Runa simi",    "region": "Latin America", "rtl": False, "flag": "🌎"},
    {"code": "gn",  "name_en": "Guaraní",        "native": "Avañeʼẽ",      "region": "Latin America", "rtl": False, "flag": "🇵🇾"},

    # ── Major host-country languages ──────────────────────────────────
    {"code": "en", "name_en": "English",  "native": "English",   "region": "Host-country languages", "rtl": False, "flag": "🇬🇧"},
    {"code": "de", "name_en": "German",   "native": "Deutsch",   "region": "Host-country languages", "rtl": False, "flag": "🇩🇪"},
    {"code": "fr", "name_en": "French",   "native": "Français",  "region": "Host-country languages", "rtl": False, "flag": "🇫🇷"},
    {"code": "it", "name_en": "Italian",  "native": "Italiano",  "region": "Host-country languages", "rtl": False, "flag": "🇮🇹"},
    {"code": "nl", "name_en": "Dutch",    "native": "Nederlands","region": "Host-country languages", "rtl": False, "flag": "🇳🇱"},
    {"code": "sv", "name_en": "Swedish",  "native": "Svenska",   "region": "Host-country languages", "rtl": False, "flag": "🇸🇪"},
    {"code": "no", "name_en": "Norwegian","native": "Norsk",     "region": "Host-country languages", "rtl": False, "flag": "🇳🇴"},
    {"code": "fi", "name_en": "Finnish",  "native": "Suomi",     "region": "Host-country languages", "rtl": False, "flag": "🇫🇮"},
    {"code": "el", "name_en": "Greek",    "native": "Ελληνικά",  "region": "Host-country languages", "rtl": False, "flag": "🇬🇷"},

    # ── Custom / tribal / unlisted (free-text) ────────────────────────
    {"code": "custom", "name_en": "Other / Tribal / Indigenous (specify)",
     "native": "—", "region": "Other", "rtl": False, "flag": "🗣️"},
]


# Quick lookup map
_BY_CODE: dict[str, LanguageEntry] = {e["code"]: e for e in SUPPORTED_LANGUAGES}


def get_language_entry(code: str | None) -> LanguageEntry | None:
    """Return the language entry for a code, or None if not registered."""
    if not code:
        return None
    return _BY_CODE.get(code)


def language_name(code: str | None, language_other: str | None = None) -> str:
    """Best-effort English display name for a (code, custom) pair.

    - If code == "custom" and `language_other` is provided, returns that
      free-text label (used for tribal / unlisted languages).
    - If code is registered, returns its English display name.
    - Otherwise falls back to the raw code or "Unknown".
    """
    if code == "custom":
        return (language_other or "").strip() or "Unspecified language"
    entry = get_language_entry(code)
    if entry:
        return entry["name_en"]
    return (code or "Unknown").strip() or "Unknown"


def resolve_language(code: str | None, language_other: str | None = None) -> dict:
    """Resolve a stored (code, language_other) pair into a rich descriptor.

    Returns a dict with `code`, `display_name`, `native`, `rtl` — safe to
    embed in AI prompts, PDFs, and JSON responses.
    """
    if code == "custom":
        label = (language_other or "").strip() or "Unspecified language"
        return {
            "code": "custom",
            "display_name": label,
            "native": label,
            "rtl": False,
            "is_custom": True,
        }
    entry = get_language_entry(code)
    if entry:
        return {
            "code": entry["code"],
            "display_name": entry["name_en"],
            "native": entry["native"],
            "rtl": entry["rtl"],
            "is_custom": False,
        }
    fallback = (code or "Unknown").strip() or "Unknown"
    return {
        "code": fallback,
        "display_name": fallback,
        "native": fallback,
        "rtl": False,
        "is_custom": False,
    }


def grouped_for_ui() -> list[dict]:
    """Return languages grouped by region for use in a <select><optgroup>.

    Shape: [{"region": "...", "languages": [LanguageEntry, ...]}, ...]
    Order preserved from SUPPORTED_LANGUAGES.
    """
    groups: dict[str, list[LanguageEntry]] = {}
    order: list[str] = []
    for entry in SUPPORTED_LANGUAGES:
        region = entry["region"]
        if region not in groups:
            groups[region] = []
            order.append(region)
        groups[region].append(entry)
    return [{"region": r, "languages": groups[r]} for r in order]
