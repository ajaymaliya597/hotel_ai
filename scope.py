"""Context-aware hotel-management scope guard for Nova (standard library only)."""
from __future__ import annotations
import re
from typing import Any

def _rx(p: str) -> re.Pattern[str]:
    return re.compile(p, re.I | re.X)

# Classifies common hotel-management requests, including existing bookings.
INTENTS = {
 "booking": _rx(r"""
    \b(?:book|reserve|make|create)\s+(?:(?:me|us|a|the|one|hotel|room)\s+){0,3}(?:hotel|room|rooms|stay|reservation|booking)\b|
    \b(?:need|want|looking\s+for)\s+(?:a\s+)?(?:hotel\s+)?(?:room|rooms|place\s+to\s+stay)\b|
    \b(?:hotel|room|kamra|kamre)\s+chahiye\b|\bbook(?:ing)?\s+kar(?:\s+do|\s+de)?\b|
    होटल\s+(?:बुक|बुकिंग|चाहिए)|ओटल\s+(?:बुक|बुप|बक)(?:ing)?\s+कर(?:ना|ना है|ें)?|(?:कमरा|कमरे|रूम)\s+(?:बुक|चाहिए)|बुकिंग\s+कर
 """),
 "availability": _rx(r"""
    \b(?:room|rooms|hotel|hotels)\s+(?:availability|available|vacant|free)\b|
    \b(?:available|vacant|free)\s+(?:hotel\s+)?rooms?\b|
    \bdo\s+you\s+have\s+(?:any\s+)?rooms?\b|\bcheck\s+(?:room|hotel)\s+availability\b|
    \broom\s+(?:hai|available\s+hai|khaali\s+hai)\b|\bkamra\s+khaali\b|कमरे?\s+(?:उपलब्ध|खाली)
 """),
 "rates": _rx(r"""
    \b(?:room|hotel|night)\s+(?:price|rate|cost|tariff)\b|
    \b(?:price|rate|cost|tariff|rent|kiraya|budget)\s+(?:of\s+)?(?:a\s+)?(?:hotel|room|night)\b|
    \bhow\s+much\b.{0,45}\b(?:room|hotel|night|stay)\b|\bprice\s+per\s+night\b|\bkitna\s+(?:kiraya|rent|rate|price)\b
 """),
 "existing_booking": _rx(r"""
    \b(?:my|our|mera|meri|mere)\s+(?:(?:last|previous|old|existing|current|purani|pichhli)\s+)?(?:hotel\s+)?(?:booking|reservation|room)\b|
    \b(?:show|find|check|view|retrieve|track)\s+(?:(?:me|my)\s+)?(?:(?:last|previous|existing)\s+)?(?:hotel\s+)?(?:booking|reservation|booking\s+details)\b|
    \bbooking\s+(?:status|details|reference|id|code|number|confirmation)\b|
    \bconfirm\s+(?:my\s+)?(?:(?:last|previous|existing)\s+)?(?:hotel\s+)?(?:booking|reservation)\b|
    \bmeri\s+(?:purani|pichhli|last)?\s*booking\b|(?:booking|reservation)\s+(?:dikhao|batao|status)\b
 """),
 "cancellation": _rx(r"""
    \b(?:cancel|cancellation|refund|radd)\b.{0,50}\b(?:booking|reservation|room|stay|hotel|payment|advance)\b|
    \b(?:booking|reservation|room|stay)\b.{0,35}\b(?:cancel|cancellation|refund|radd)\b|बुकिंग\s+रद्द
 """),
 "modification": _rx(r"""
    \b(?:change|modify|update|edit|reschedule|extend|shorten)\b.{0,55}\b(?:booking|reservation|check.?in|check.?out|date|dates|guest|room|stay)\b|
    \b(?:booking|reservation|dates|check.?in|check.?out)\b.{0,35}\b(?:change|modify|update|reschedule|extend)\b|
    \bchange\s+(?:my\s+)?booking\b|\bbooking\s+badal\b
 """),
 "check_in_out": _rx(r"\bcheck.?in\b|\bcheck.?out\b|\bearly\s+check.?in\b|\blate\s+check.?out\b|\barrival\s+time\b|\bdeparture\s+time\b|चेक.?इन|चेक.?आउट"),
 "amenities": _rx(r"\b(?:wifi|wi-fi|internet|breakfast|parking|pool|gym|air conditioning|ac|laundry|elevator|lift|balcony|tv|hot water|pet friendly|wheelchair access|hotel facilities|hotel amenities)\b"),
 "room_service_housekeeping": _rx(r"\broom service\b|\bhousekeeping\b|\bclean(?:ing)?\s+(?:my\s+)?room\b|\bextra\s+(?:towel|blanket|pillow|bed|water)\b|\bbring\s+(?:me\s+)?(?:water|food|towels|blanket)\b|कमरा\s+साफ|तौलिया|कंबल"),
 "maintenance": _rx(r"\b(?:broken|not working|doesn't work|does not work|repair|maintenance|faulty)\b.{0,45}\b(?:ac|air conditioner|tv|wifi|shower|tap|toilet|light|door|lock|heater|room)\b|\bproblem with my room\b"),
 "restaurant_food": _rx(r"\b(?:restaurant|dining|food menu|breakfast time|lunch time|dinner time|order food|food order|food delivery)\b"),
 "payment_invoice": _rx(r"\b(?:payment|pay|paid|bill|invoice|receipt|deposit|advance|upi|refund|extra charge|gst invoice)\b.{0,45}\b(?:hotel|room|booking|reservation|bill|invoice|payment|stay|refund|charge|receipt)?\b|\b(?:hotel|booking|reservation)\b.{0,30}\b(?:payment|bill|invoice|receipt|refund)\b"),
 "policies": _rx(r"\b(?:hotel|booking|cancellation|refund|pet|smoking|visitor|child|extra bed)\s+(?:policy|rules?|allowed|permitted)\b|\bwhat is your\s+(?:cancellation|check.?in|check.?out|pet)\s+policy\b"),
 "location_directions": _rx(r"\b(?:hotel address|hotel location|where is the hotel|directions to the hotel|how do i get to the hotel|airport transfer|airport pickup|shuttle service|hotel phone number|contact the hotel)\b"),
 "complaint_feedback": _rx(r"\b(?:complaint|complain|problem|issue|not satisfied|bad service|poor service|speak to the manager|feedback|dirty room)\b.{0,60}\b(?:hotel|room|staff|service|booking|reservation|stay)?\b|\b(?:hotel|room|staff|service|booking|stay)\b.{0,30}\b(?:complaint|problem|issue|bad service|feedback)\b"),
 "lost_found": _rx(r"\b(?:lost|left|forgot|missing)\b.{0,40}\b(?:item|phone|wallet|passport|bag|luggage|charger|jacket|belongings)\b|\blost and found\b|\blost property\b"),
 "group_booking": _rx(r"\b(?:group booking|book rooms for|multiple rooms|wedding booking|conference booking|corporate booking|event accommodation|block of rooms)\b"),
 "accessibility": _rx(r"\b(?:wheelchair|accessible room|disability access|mobility assistance|step.?free access|accessible bathroom)\b"),
}

# Only explicit standalone off-topic requests are blocked. Avoid blocking a
# valid hotel request merely because a generic word appears in its sentence.
OFF_TOPIC = _rx(r"""^\s*(?:tell me (?:a )?(?:story|joke)|write (?:me )?(?:a )?(?:poem|joke|story|essay|lyrics|code|program)|compose (?:me )?(?:a )?(?:poem|joke|story|essay|lyrics)|generate (?:some )?(?:python|javascript|sql )?code|explain (?:python|javascript|sql|programming|coding)|teach (?:me )?(?:python|javascript|sql|coding|programming)|what(?:'s| is) (?:the )?weather(?: like)?|(?:give|show|tell) me (?:the )?(?:latest )?news|tell me about politics|solve this equation|make an image|draw me)\s*[.!?]*$""")

YES_NO = _rx(r"""^\s*(?:yes|yeah|yep|yup|sure|okay|ok|alright|right|correct|confirmed|confirm|please do|go ahead|do it|book it|cancel it|proceed|no|nope|nah|not now|don't|do not|haan|han|ji|jee|haan\s+ji|theek|theek hai|achha|acha|nahi|nahin|kar do|kar de|kar dena|haan book kar do|confirm kar do|pakka|हाँ|हां|जी|नहीं|नही|ठीक है|कर दो)\s*[.!?।؟]*$""")
SHORT = _rx(r"""^\s*(?:same|same dates|wahi|wohi|usi|aur|kitna|kitne|today|tomorrow|tonight|next week|next month|kal|parso|aaj|परसों|कल|आज|first room|second room|choose room|select room|pehla room|dusra room|single|singal|singel|double|dubble|deluxe|delux|deluce|suite|suit|standard|queen|king|twin|family|सिंगल|डबल|डीलक्स|सुइट|\d{1,4}(?:\s*(?:people|persons|guests|adults|nights?|rooms?|log|logo|aadmi|admi|din|raat|मेहमान|लोग|दिन|रात))?|\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?|\d{4}-\d{2}-\d{2}|(?:my name is|name is|mera naam|मेरा नाम)\s+.{2,70}|(?:my phone is|phone number is|mobile number is)\s+.{3,100} )\s*[.!?।؟]*$""")


def normalize_hotel_transcript(transcript: str) -> str:
    """Repair a small, conservative set of common speech-recognition errors for hotel intent.

    Only rewrites short phrases that strongly resemble a hotel-booking command; it does not
    rewrite names, dates, phone numbers, or arbitrary conversation text.
    """
    raw = (transcript or "").strip()
    folded = raw.lower().replace("’", "'")
    compact = re.sub(r"[^\w\s]", " ", folded, flags=re.UNICODE)
    compact = re.sub(r"\s+", " ", compact).strip()

    # Common multilingual Whisper mis-hearings observed in Nova sessions.
    phonetic_booking = re.search(
        r"(?:h[oó]tel|hotel|hotal|ओटल|होटल|کا اٹل|கோட்டல்|హోటల్).{0,24}"
        r"(?:b[uú]kk?arna|b[uú]kk?arna|b[oó]okarna|buk karna|booking karna|"
        r"bukkarna|bup karna|बुक करना|बुकिंग करना|बुक करना है)",
        compact, re.I,
    )
    if phonetic_booking:
        return "Book a hotel"

    # Standalone voice-menu phrases should start the booking flow, not require the LLM
    # to infer what the button meant.
    if re.fullmatch(r"(?:book a hotel|hotel booking|book hotel|book a room|hotel book karna|hotel booking karna)[.!? ]*", compact, re.I):
        return "Book a hotel"
    return raw

def classify_hotel_intent(transcript: str) -> str | None:
    text = (transcript or "").strip()
    if not text or OFF_TOPIC.fullmatch(text):
        return None
    lower = text.lower()
    if re.search(r"\broom service\b|\bhousekeeping\b|\bclean(?:ing)?\s+(?:my\s+)?room\b", lower):
        return "room_service_housekeeping"
    if re.search(r"\b(?:not working|doesn't work|does not work|broken|repair|maintenance|faulty)\b", lower) and re.search(r"\b(?:ac|air conditioner|tv|wifi|shower|tap|toilet|light|door|lock|heater|room)\b", lower):
        return "maintenance"
    if re.search(r"\bwhere is (?:the )?hotel(?: address)?\b|\bhotel address\b", lower):
        return "location_directions"
    if re.search(r"\b(?:i need|i want|need|want|make|create) (?:a )?group booking\b|\bgroup booking\b", lower):
        return "group_booking"
    # Specific service/action intents must win over broad words such as "room",
    # "booking", "AC", or "my booking".
    priority = (
        "cancellation", "modification", "payment_invoice", "maintenance",
        "room_service_housekeeping", "restaurant_food", "location_directions",
        "complaint_feedback", "lost_found", "group_booking", "accessibility",
        "policies", "check_in_out", "amenities", "rates", "availability",
        "existing_booking", "booking",
    )
    for name in priority:
        if INTENTS[name].search(text):
            return name
    return None

def is_explicitly_non_booking(transcript: str) -> bool:
    text = (transcript or "").strip().lower().rstrip(".!? ")
    if not text:
        return False
    phrases = (
        "tell me a story", "tell me story", "tell me a joke", "write a poem",
        "write me a poem", "write a story", "write me a story", "write an essay",
        "write code", "write a program", "compose a poem", "generate code",
        "explain python", "explain javascript", "explain sql",
        "explain programming", "explain coding", "teach me python",
        "teach python", "teach me javascript", "what is the weather",
        "what's the weather", "give me the news", "show me the news",
        "tell me the news", "tell me about politics", "solve this equation",
        "make an image", "draw me",
    )
    return any(text == phrase or text.startswith(phrase + " ") for phrase in phrases)

def _history(history: list[dict[str, Any]] | None) -> list[dict[str, str]]:
    out = []
    for item in (history or [])[-10:]:
        if isinstance(item, dict) and item.get("role") in {"user", "assistant"} and isinstance(item.get("content"), str):
            if item["content"].strip():
                out.append({"role": item["role"], "content": item["content"].strip()})
    return out

def _hotel_context(history: list[dict[str, str]]) -> bool:
    if any(x["role"] == "user" and classify_hotel_intent(x["content"]) for x in history[-10:]):
        return True
    phrases = ("check-in", "check in", "check-out", "check out", "check in date", "check out date",
               "how many guests", "how many people", "guest count", "number of guests",
               "which room", "choose a room", "select a room", "room type", "which type of room",
               "what type of room", "single, double", "deluxe", "your full name", "guest name",
               "phone number", "mobile number", "contact number", "confirm your booking",
               "confirm the booking", "booking summary", "booking reference", "room service",
               "repeat the last booking detail", "couldn't finish that step", "hotel booking",
               "aapki check-in date", "check-out date, please", "kitne mehmaan", "kitne log",
               "kis type ka kamra", "kaunsa kamra", "kaun sa kamra", "कितने मेहमान",
               "कौन सा कमरा", "कौन-सा कमरा", "किस प्रकार का कमरा", "बुकिंग की पुष्टि")
    return any(x["role"] == "assistant" and any(p in x["content"].lower() for p in phrases) for x in history[-5:])

def _contextual_followup(text: str, history: list[dict[str, str]]) -> bool:
    if not _hotel_context(history):
        return False
    normalized_text = re.sub(r"\s+", " ", (text or "").strip().lower())
    if re.fullmatch(r"(?:show|tell|repeat|say) me (?:the )?(?:last|previous) (?:detail|step|question|answer)(?: again)?[.!? ]*", normalized_text):
        return True
    last = next((x["content"].lower() for x in reversed(history) if x["role"] == "assistant"), "")
    if not last:
        return False

    # A short room preference is a valid answer only immediately after Nova asks for
    # the room type. Keep this contextual so words like "single" elsewhere are not
    # accidentally treated as hotel intent.
    room_type_prompt = bool(re.search(
        r"room\s*type|which\s+(?:type|kind)\s+of\s+room|what\s+(?:type|kind)\s+of\s+room|"
        r"choose\s+(?:a\s+)?room|select\s+(?:a\s+)?room|single\s*[,/].{0,35}double|"
        r"kis\s+type\s+ka\s+kamra|kaun(?:sa|\s+sa)\s+kamra|kamra\s+chah(?:e|enge)|"
        r"किस प्रकार का कमरा|कौन-?सा कमरा|कमरा चुनें|सिंगल.*डबल|डीलक्स",
        last, re.I,
    ))
    room_answer = re.fullmatch(
        r"\s*(?:a\s+)?(?:single|singal|singel|double|dubble|deluxe|delux|deluce|deluxee|"
        r"suite|suit|standard|queen|king|twin|family|single room|double room|deluxe room|suite room|"
        r"सिंगल|सिंगल रूम|डबल|डबल रूम|डीलक्स|डीलक्स रूम|सुइट|स्टैंडर्ड)\s*[.!? ]*",
        normalized_text, re.I,
    )
    if room_type_prompt and room_answer:
        return True

    confirm_prompt = any(p in last for p in ("confirm", "shall i", "should i", "would you like", "proceed", "booking summary", "is this correct", "क्या मैं", "पुष्टि"))
    asks_question = "?" in last or any(p in last for p in ("which", "what", "how many", "please provide", "tell me", "select", "choose", "कितने", "कौन", "बताइए"))
    if YES_NO.fullmatch(text):
        return confirm_prompt or asks_question
    if SHORT.fullmatch(text) and (asks_question or confirm_prompt):
        return True
    digit_text = text.translate(str.maketrans("०१२३४५६७८९", "0123456789"))
    if any(p in last for p in ("check-in", "check in", "check-out", "check out", "what dates", "which dates", "date", "तारीख")):
        if re.search(
            r"\b(?:today|tomorrow|tonight|day after tomorrow|next week|kal|parso|aaj|आज|कल|परसों)\b|"
            r"\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b|\b\d{4}-\d{1,2}-\d{1,2}\b|"
            r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|"
            r"jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t|tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+20\d{2}\b|"
            r"\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|"
            r"sep(?:t|tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+\d{1,2}(?:st|nd|rd|th)?[,]?\s+20\d{2}\b",
            digit_text, re.I,
        ):
            return True
    if any(p in last for p in ("how many guests", "number of guests", "how many people", "guest count", "कितने मेहमान")):
        return bool(re.fullmatch(r"\s*\d{1,2}\s*(?:people|persons|guests|adults|log|logo|aadmi|admi|मेहमान|लोग)?\s*", digit_text, re.I))
    if any(p in last for p in ("full name", "your name", "guest name", "आपका नाम")):
        return bool(re.fullmatch(r"[A-Za-z][A-Za-z .'-]{1,70}", text.strip()))
    if any(p in last for p in ("phone", "mobile number", "contact number", "booking code", "booking reference", "फोन")):
        return bool(re.search(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", text, re.I) or re.search(r"\b(?:\+?91[\s-]?)?[6-9]\d{9}\b", text) or re.search(r"\bNOVA-[A-Z0-9]{4,20}\b", text, re.I))
    return False

def is_hotel_booking_related(transcript: str, history: list[dict[str, Any]] | None) -> bool:
    text = normalize_hotel_transcript(transcript).strip()
    if not text or OFF_TOPIC.fullmatch(text):
        return False
    if classify_hotel_intent(text):
        return True
    return _contextual_followup(text, _history(history))

# def out_of_scope_reply(language: str) -> str:
#     language = (language or "en").lower()
#     if language in {"hi", "hindi"}:
#         return "मैं होटल बुकिंग, उपलब्धता, दरों, मौजूदा आरक्षण और ठहरने से जुड़ी सेवाओं में मदद कर सकता हूँ।"
#     if language in {"hinglish", "hi-en"}:
#         return "Main hotel booking, availability, rates, existing reservations aur stay-related services mein help kar sakta hoon."
#     if language in {"ta", "tamil"}:
#         return "நான் ஹோட்டல் முன்பதிவு, அறை கிடைப்புத் தன்மை, கட்டணங்கள் மற்றும் தங்கும் சேவைகளில் உதவ முடியும்."
#     if language in {"te", "telugu"}:
#         return "నేను హోటల్ బుకింగ్, గదుల లభ్యత, ధరలు మరియు బస సేవలలో సహాయం చేయగలను."
#     return "I can help with hotel bookings, availability, rates, existing reservations, room service, hotel facilities, payments, and stay-related requests."
