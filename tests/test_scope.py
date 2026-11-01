import unittest
from scope import is_hotel_booking_related, is_explicitly_non_booking


class ScopeGuardTests(unittest.TestCase):
    def test_direct_booking_intents(self):
        for text in [
            "Book a hotel room",
            "I need a room for tomorrow",
            "Cancel my reservation",
            "Confirm my last booking",
            "Show me my previous reservation",
            "Meri purani booking batao",
            "Kal ke liye room chahiye",
            "मुझे कमरा चाहिए",
        ]:
            with self.subTest(text=text):
                self.assertTrue(is_hotel_booking_related(text, []))

    def test_yes_requires_hotel_context_and_prompt(self):
        history = [
            {"role": "user", "content": "I want to book a hotel room"},
            {"role": "assistant", "content": "Your booking summary is ready. Shall I confirm the booking?"},
        ]
        self.assertTrue(is_hotel_booking_related("yes", history))
        self.assertTrue(is_hotel_booking_related("haan ji", history))
        self.assertFalse(is_hotel_booking_related("yes", []))

    def test_slot_answers_need_matching_question(self):
        history = [
            {"role": "user", "content": "Book a hotel room"},
            {"role": "assistant", "content": "How many guests will stay?"},
        ]
        self.assertTrue(is_hotel_booking_related("2 guests", history))
        self.assertFalse(is_hotel_booking_related("weather", history))

    def test_unrelated_request(self):
        self.assertTrue(is_explicitly_non_booking("Tell me a story"))
        self.assertFalse(is_hotel_booking_related("Tell me a story", []))
        self.assertFalse(is_hotel_booking_related("What is the weather like?", []))

    def test_common_hindi_voice_transcription_typos_for_hotel_booking(self):
        from scope import is_hotel_booking_related, normalize_hotel_transcript
        self.assertTrue(is_hotel_booking_related("ओटल बुप करना", []))
        self.assertEqual(normalize_hotel_transcript("Hótel búkkarna"), "Book a hotel")
        self.assertTrue(is_hotel_booking_related("Hótel búkkarna", []))
        self.assertTrue(is_hotel_booking_related("Book a Hotel", []))

    def test_short_acknowledgement_is_not_misclassified_as_hotel_intent(self):
        from scope import is_hotel_booking_related
        self.assertFalse(is_hotel_booking_related("Mm-hmm", []))

    def test_show_last_detail_is_contextual_followup(self):
        from scope import is_hotel_booking_related
        history = [
            {"role": "user", "content": "Book a hotel"},
            {"role": "assistant", "content": "I couldn't finish that step. Please repeat the last booking detail."},
        ]
        self.assertTrue(is_hotel_booking_related("Show me the last detail", history))

    def test_room_type_answers_are_contextual_hotel_followups(self):
        history = [
            {"role": "user", "content": "book hotel"},
            {"role": "assistant", "content": "Aap kis type ka kamra chahenge? (Single, Double, Deluxe, Suite)"},
        ]
        for answer in ["single", "Single", "double", "Deluxe", "Deluce", "Delux", "suite", "single room"]:
            with self.subTest(answer=answer):
                self.assertTrue(is_hotel_booking_related(answer, history))

    def test_room_type_words_without_room_question_are_not_automatically_hotel_intent(self):
        self.assertFalse(is_hotel_booking_related("single", []))
        self.assertFalse(is_hotel_booking_related("deluxe", []))

    def test_combined_checkout_date_and_guest_answer_keeps_context(self):
        history = [
            {"role": "user", "content": "book hotel"},
            {"role": "assistant", "content": "Check-out date, please? Aap kitne mehmaan aayenge?"},
        ]
        self.assertTrue(is_hotel_booking_related("27 Oct 2026, 2 log hai", history))


if __name__ == "__main__":
    unittest.main()
