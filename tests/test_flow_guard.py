import unittest
from flow_guard import _has_active_hotel_flow, _explicit_confirmation


class VoiceFlowGuardTests(unittest.TestCase):
    def test_hindi_date_answer_keeps_booking_context(self):
        history = [
            {"role": "user", "content": "होटल बुक करने हैं"},
            {"role": "assistant", "content": "ज़रूर, कृपया अपना चेक-इन दिनांक बताइए (DD MMM YYYY)।"},
        ]
        self.assertTrue(_has_active_hotel_flow(history))

    def test_hinglish_room_type_prompt_keeps_booking_flow_active(self):
        history = [
            {"role": "user", "content": "book hotel"},
            {"role": "assistant", "content": "Aap kis type ka kamra chahenge? (Single, Double, Deluxe, Suite)"},
        ]
        self.assertTrue(_has_active_hotel_flow(history))

    def test_combined_slot_question_keeps_flow_active(self):
        history = [
            {"role": "user", "content": "26 Oct 2026"},
            {"role": "assistant", "content": "Check-out date, please? Aap kitne mehmaan aayenge?"},
        ]
        self.assertTrue(_has_active_hotel_flow(history))

    def test_completed_booking_does_not_keep_flow_active(self):
        history = [
            {"role": "user", "content": "Book a hotel in Jaipur"},
            {"role": "assistant", "content": "Your booking is confirmed. Code NOVA-AB12. Room 101, check-in 26 Oct 2026, check-out 27 Oct 2026."},
        ]
        self.assertFalse(_has_active_hotel_flow(history))

    def test_booking_confirmation_requires_prior_confirmation_question_for_yes(self):
        history = [{"role": "assistant", "content": "Should I confirm the booking?"}]
        self.assertTrue(_explicit_confirmation("booking", "yes", history))
        self.assertFalse(_explicit_confirmation("booking", "yes", [{"role": "assistant", "content": "What is your check-in date?"}]))
        self.assertFalse(_explicit_confirmation("booking", "confirm booking", [{"role": "assistant", "content": "What is your check-in date?"}]))
        final_prompt = [{"role": "assistant", "content": "Room 201, check-in 2026-10-26, check-out 2026-10-27, 2 guests, guest name Ajay Maliya, mobile 9876543210, total price ₹3,999. Please confirm if you'd like to finalize this booking."}]
        self.assertTrue(_explicit_confirmation("booking", "Confirm.", final_prompt))
        self.assertFalse(_explicit_confirmation("booking", "Confirm.", [{"role": "assistant", "content": "What is your check-out date?"}]))

    def test_booking_confirmation_rejects_negation_and_past_success(self):
        prompt = [{"role": "assistant", "content": "Should I book this room?"}]
        self.assertFalse(_explicit_confirmation("booking", "No, don't book it", prompt))
        self.assertFalse(_explicit_confirmation("booking", "don't confirm booking", prompt))
        self.assertFalse(_explicit_confirmation("booking", "I don't want you to book it", prompt))
        self.assertFalse(_explicit_confirmation("booking", "booking mat karna", prompt))
        self.assertFalse(_explicit_confirmation("booking", "yes", [{"role": "assistant", "content": "Your booking is confirmed. Code NOVA-1234."}]))

    def test_cancel_confirmation_requires_action_specific_prompt(self):
        self.assertTrue(_explicit_confirmation("cancel", "हाँ", [{"role": "assistant", "content": "क्या मैं यह बुकिंग रद्द कर दूँ?"}]))
        self.assertFalse(_explicit_confirmation("cancel", "हाँ", [{"role": "assistant", "content": "What is the booking mobile number?"}]))
        self.assertFalse(_explicit_confirmation("cancel", "yes", [{"role": "assistant", "content": "Should I book this room?"}]))

    def test_cancel_confirmation_rejects_negative_intent(self):
        prompt = [{"role": "assistant", "content": "Should I cancel this booking?"}]
        self.assertFalse(_explicit_confirmation("cancel", "No, don't cancel it", prompt))
        self.assertFalse(_explicit_confirmation("cancel", "I don't want you to cancel it", prompt))
        self.assertFalse(_explicit_confirmation("cancel", "cancel mat karna", prompt))
        self.assertFalse(_explicit_confirmation("cancel", "मत रद्द करना", [{"role": "assistant", "content": "क्या मैं यह बुकिंग रद्द कर दूँ?"}]))
        self.assertFalse(_explicit_confirmation("cancel", "not yet", prompt))


    def test_active_confirmation_survives_when_initial_booking_intent_is_outside_window(self):
        history = [
            {"role": "user", "content": "2026-10-26"},
            {"role": "assistant", "content": "What is your check-out date?"},
            {"role": "user", "content": "2026-10-27"},
            {"role": "assistant", "content": "How many guests?"},
            {"role": "user", "content": "2"},
            {"role": "assistant", "content": "Choose room 201?"},
            {"role": "user", "content": "201"},
            {"role": "assistant", "content": "Please confirm booking for check-in 2026-10-26, check-out 2026-10-27, 2 guests, room 201, total ₹3999. Shall I confirm?"},
        ]
        self.assertTrue(_has_active_hotel_flow(history))

if __name__ == "__main__":
    unittest.main()
