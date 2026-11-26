"""
Multilingual notification templates.

Supported languages: en, hi, pa (Punjabi in Gurmukhi script)
Supported templates:
  - match_confirmed   : pickup confirmed, tell farmer date and price
  - match_proposed    : new match proposed awaiting confirmation
  - burn_alert        : fire detected in village
  - daily_digest      : daily harvest window summary for officer
"""
from string import Formatter

_TEMPLATES: dict[str, dict[str, str]] = {
    "match_confirmed": {
        "en": (
            "Good news! {buyer_name} will collect your paddy straw on {pickup_date}. "
            "You will receive ₹{price} per tonne. Contact your block officer for details."
        ),
        "hi": (
            "शुभ समाचार! {buyer_name} आपके धान के पराली को {pickup_date} को उठाएगा। "
            "आपको प्रति टन ₹{price} मिलेगा। विवरण के लिए अपने ब्लॉक अधिकारी से संपर्क करें।"
        ),
        "pa": (
            "ਖੁਸ਼ਖਬਰੀ! {buyer_name} ਤੁਹਾਡੀ ਪਰਾਲੀ {pickup_date} ਨੂੰ ਚੁੱਕੇਗਾ। "
            "ਤੁਹਾਨੂੰ ₹{price} ਪ੍ਰਤੀ ਟਨ ਮਿਲੇਗਾ। ਜ਼ਿਆਦਾ ਜਾਣਕਾਰੀ ਲਈ ਆਪਣੇ ਬਲਾਕ ਅਧਿਕਾਰੀ ਨਾਲ ਸੰਪਰਕ ਕਰੋ।"
        ),
    },
    "match_proposed": {
        "en": (
            "A buyer has been found for your straw. {buyer_name} proposes to pick up "
            "{tonnes} tonnes on {pickup_date} at ₹{price}/tonne. Reply YES to confirm."
        ),
        "hi": (
            "आपकी पराली के लिए एक खरीदार मिला है। {buyer_name} {pickup_date} को "
            "{tonnes} टन ₹{price}/टन पर लेने का प्रस्ताव रखता है। पुष्टि करने के लिए YES भेजें।"
        ),
        "pa": (
            "ਤੁਹਾਡੀ ਪਰਾਲੀ ਲਈ ਖਰੀਦਦਾਰ ਮਿਲਿਆ। {buyer_name} {pickup_date} ਨੂੰ "
            "{tonnes} ਟਨ ₹{price}/ਟਨ 'ਤੇ ਚੁੱਕਣਾ ਚਾਹੁੰਦਾ ਹੈ। ਪੁਸ਼ਟੀ ਕਰਨ ਲਈ YES ਭੇਜੋ।"
        ),
    },
    "burn_alert": {
        "en": (
            "⚠️ Fire alert: burning detected near {village_name} on {detected_on}. "
            "Confidence: {confidence}. Please contact your block officer immediately."
        ),
        "hi": (
            "⚠️ आग की चेतावनी: {detected_on} को {village_name} के पास जलाना पाया गया। "
            "विश्वसनीयता: {confidence}। कृपया तुरंत अपने ब्लॉक अधिकारी से संपर्क करें।"
        ),
        "pa": (
            "⚠️ ਅੱਗ ਦੀ ਚੇਤਾਵਨੀ: {detected_on} ਨੂੰ {village_name} ਨੇੜੇ ਅੱਗ ਲੱਗੀ। "
            "ਭਰੋਸੇਯੋਗਤਾ: {confidence}। ਕਿਰਪਾ ਕਰਕੇ ਤੁਰੰਤ ਆਪਣੇ ਬਲਾਕ ਅਧਿਕਾਰੀ ਨਾਲ ਸੰਪਰਕ ਕਰੋ।"
        ),
    },
    "daily_digest": {
        "en": (
            "Daily digest ({date}): {villages_ready} villages ready to harvest, "
            "{matches_pending} matches awaiting confirmation, "
            "{burns_today} burn events detected today."
        ),
        "hi": (
            "दैनिक सारांश ({date}): {villages_ready} गाँव कटाई के लिए तैयार, "
            "{matches_pending} मिलान पुष्टि की प्रतीक्षा में, "
            "{burns_today} आग की घटनाएं आज पाई गईं।"
        ),
        "pa": (
            "ਰੋਜ਼ਾਨਾ ਸਾਰ ({date}): {villages_ready} ਪਿੰਡ ਵਾਢੀ ਲਈ ਤਿਆਰ, "
            "{matches_pending} ਮੇਲ ਪੁਸ਼ਟੀ ਦੀ ਉਡੀਕ ਵਿੱਚ, "
            "{burns_today} ਅੱਜ ਅੱਗ ਦੀਆਂ ਘਟਨਾਵਾਂ ਮਿਲੀਆਂ।"
        ),
    },
}

_FALLBACK_LANGUAGE = "en"


def render_message(language: str, template: str, **kwargs) -> str:
    """
    Return the rendered notification string.

    Args:
        language:  "en" | "hi" | "pa"
        template:  key from _TEMPLATES
        **kwargs:  placeholder values, e.g. pickup_date="2026-10-24", price=1500
    """
    lang = language if language in ("en", "hi", "pa") else _FALLBACK_LANGUAGE
    tmpl_group = _TEMPLATES.get(template)
    if tmpl_group is None:
        return f"[unknown template: {template}]"
    tmpl = tmpl_group.get(lang) or tmpl_group.get(_FALLBACK_LANGUAGE, "")
    try:
        return tmpl.format(**kwargs)
    except KeyError as exc:
        return f"[template error – missing key {exc}] {tmpl}"
