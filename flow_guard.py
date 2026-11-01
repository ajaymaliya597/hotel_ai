"""Conversation-state and explicit-confirmation guards for Nova's hotel workflows."""
from __future__ import annotations

import re


def _last_assistant_message(history: list[dict]) -> str:
    for item in reversed(history or []):
        if isinstance(item, dict) and item.get("role") == "assistant" and isinstance(item.get("content"), str):
            return item["content"].strip()
    return ""


def _has_active_hotel_flow(history: list[dict]) -> bool:
    """Return true only when the *latest assistant turn* is still asking for a booking slot/action.
    Earlier versions searched all assistant messages for words like "check-in" and "room".
    That left the flow active even after a reservation was completed, allowing unrelated follow-ups
    to bypass the deterministic scope guard.
    """
    recent = [x for x in (history or [])[-10:] if isinstance(x, dict)]
    # Do not require the original booking-intent message to remain in the short
    # history window. A normal booking can take 6+ turns, so the first user turn
    # is often evicted before the final Yes/No confirmation. The latest assistant
    # prompt plus the completion check below is the reliable active-state signal.
    assistant = _last_assistant_message(recent)
    if not assistant:
        return False
    # Confirmation/slot prompts, rather than status summaries, are the only active states.
    slot_topic = re.search(
        r"check.?in|check.?out|date|guest|people|full name|your name|mobile|phone|"
        r"choose a room|which room|room number|room type|single|double|deluxe|suite|"
        r"which type|what type|select a room|select room|booking code|confirm|book it|cancel|"
        r"check.?in date|check.?out date|guest count|contact number|"
        r"चेक.?इन|चेक.?आउट|दिनांक|तिथि|तारीख|मेहमान|नाम|फोन|कमरा|कमरे|किस प्रकार|किस टाइप|"
        r"कौन सा कमरा|कौन-सा कमरा|सिंगल|डबल|डीलक्स|सुइट|बुकिंग|रद्द|कैंसल|मोबाइल",
        assistant, re.I,
    )
    prompt_marker = re.search(
        r"\?|\b(?:please|tell me|provide|share|enter|choose|select|which|what|how many|"
        r"may i|can i|shall i|should i|would you like|do you want|let me know|confirm|"
        r"which type|what type|which kind|choose a room|select a room|tell me your|"
        r"what is your|what's your|could you|can you|please share|please tell)\b|"
        r"कृपया|बताइए|बताएं|बताओ|कितने|क्या मैं|क्या आप|चाहते हैं|कर दूँ|करूं|करूँ|"
        r"किस प्रकार|किस टाइप|कौन सा|कौन-सा|चाहिए|चाहेंगे|बताइएगा",
        assistant, re.I,
    )
    # A successful booking/cancellation sentence must not keep a flow active merely because
    # its summary includes the booking dates or room number.
    completion = re.search(
        r"\b(?:is confirmed|has been confirmed|confirmed successfully|has been cancelled|"
        r"was cancelled|booking confirmed|reservation confirmed)\b|"
        r"बुकिंग.*(?:कन्फर्म हो गई|पुष्टि हो गई|रद्द कर दी गई)|"
        r"बुकिंग.*(?:cancel ho gayi|confirm ho gayi)",
        assistant, re.I,
    )
    return bool(slot_topic and prompt_marker and not completion)


def _is_negated_action(action: str, text: str) -> bool:
    """Detect common English/Hindi/Hinglish opt-outs before considering confirmation words."""
    if action == "booking":
        patterns = (
            r"\b(?:don't|dont|do not|never|no need to|not)\s+(?:(?:please|just)\s+)?"
            r"(?:book|confirm|reserve|finali[sz]e)\b",
            r"\b(?:don't|dont|do not|never)\s+(?:want|wish)\s+(?:you\s+)?to\s+(?:book|confirm|reserve)\b",
            r"\b(?:book|booking|confirm|reserve)\b.{0,24}\bmat\b|\bmat\s+(?:book|booking|confirm|reserve)\b",
            r"\bnot\s+yet\b|\bwait\b|\bstop\b",
            r"(?:बुक|कन्फर्म|पक्का).{0,20}(?:मत|नहीं)|(?:मत|नहीं).{0,20}(?:बुक|कन्फर्म|पक्का)",
            r"\b(?:mat|nahi)\s+(?:book|confirm|reserve)\b",
        )
    else:
        patterns = (
            r"\b(?:don't|dont|do not|never|no need to|not)\s+(?:(?:please|just)\s+)?cancel\b",
            r"\b(?:don't|dont|do not|never)\s+(?:want|wish)\s+(?:you\s+)?to\s+cancel\b",
            r"\b(?:cancel|cancellation)\b.{0,24}\bmat\b|\bmat\s+(?:cancel|cancell?)\b",
            r"\bnot\s+yet\b|\bwait\b|\bstop\b",
            r"(?:रद्द|कैंसल|कैंसिल).{0,24}(?:मत|नहीं)|(?:मत|नहीं).{0,24}(?:रद्द|कैंसल|कैंसिल)",
            r"\b(?:cancel|cancell?ing)\s+mat\s+(?:karo|karna)\b|\bmat\s+(?:cancel|cancell?)\b",
        )
    return any(re.search(pattern, text, re.I) for pattern in patterns)


def _user_explicitly_confirmed(action: str, transcript: str) -> bool:
    text = re.sub(r"\s+", " ", (transcript or "").strip().lower())
    if not text or _is_negated_action(action, text):
        return False

    if action == "booking":
        explicit = re.search(
            r"\b(?:confirm(?: the)? booking|confirm|book it|yes[, ]+confirm|yes[, ]+book|"
            r"go ahead and book|please book it|confirm kar do|haan book karo|han book karo)\b|"
            r"बुक कर दो|बुकिंग कन्फर्म|कन्फर्म कर दो|पक्का कर दो|बुक कर दीजिए",
            text, re.I,
        )
    else:
        explicit = re.search(
            r"\b(?:cancel (?:it|the booking|my booking)|yes[, ]+cancel|cancel kar do|"
            r"go ahead and cancel|please cancel it)\b|"
            r"हाँ रद्द|हां रद्द|रद्द कर दो|कैंसल कर दो|कैंसिल कर दो|रद्द कर दीजिए",
            text, re.I,
        )
    if explicit:
        return True
    return bool(re.fullmatch(
        r"(?:yes|yeah|yep|sure|please do|haan|han|haan ji|ji haan|हाँ|हां|जी हाँ|जी हां|ठीक है|कर दो)[.!\s]*",
        text, re.I,
    ))


def _assistant_asked_for_confirmation(action: str, history: list[dict]) -> bool:
    """Require a recent, action-specific confirmation question—not a past success message."""
    text = _last_assistant_message(history).lower()
    if not text:
        return False
    if action == "booking":
        prompt = re.search(
            r"\b(?:shall i|should i|can i|may i|would you like me to|do you want me to)\s+"
            r"(?:go ahead and\s+)?(?:book|confirm|reserve)\b|"
            r"\b(?:please|kindly)\s+confirm\s+(?:the\s+)?booking\b|"
            r"\bplease confirm if you(?: would like to|\x27d like to) finalize this booking\b|"
            r"\bconfirm if you(?: would like to|\x27d like to) finalize this booking\b|"
            r"\b(?:book|confirm|reserve)\b.{0,90}\?|"
            r"क्या मैं.{0,70}(?:बुक|पक्का|कन्फर्म).{0,30}(?:\?|दूँ|करूँ|करूं)|"
            r"(?:बुक|कन्फर्म).{0,50}(?:कर दूँ|करूं|करूँ|\?)",
            text, re.I,
        )
        return bool(prompt and not re.search(r"\b(?:is confirmed|has been confirmed|booking confirmed)\b", text))

    prompt = re.search(
        r"\b(?:shall i|should i|can i|may i|would you like me to|do you want me to)\s+"
        r"(?:go ahead and\s+)?cancel\b|"
        r"\b(?:please|kindly)\s+confirm\s+(?:that\s+)?(?:i can\s+)?cancel\b|"
        r"\bcancel\b.{0,90}\?|"
        r"क्या मैं.{0,70}(?:रद्द|कैंसल|कैंसिल).{0,30}(?:\?|दूँ|करूँ|करूं)|"
        r"(?:रद्द|कैंसल|कैंसिल).{0,50}(?:कर दूँ|करूं|करूँ|\?)",
        text, re.I,
    )
    return bool(prompt and not re.search(r"\b(?:has been cancelled|was cancelled|booking cancelled)\b", text))


def _explicit_confirmation(action: str, transcript: str, history: list[dict]) -> bool:
    """Require a non-negated confirmation in this turn and a matching previous prompt."""
    if action not in {"booking", "cancel"}:
        return False
    return _user_explicitly_confirmed(action, transcript) and _assistant_asked_for_confirmation(action, history)
