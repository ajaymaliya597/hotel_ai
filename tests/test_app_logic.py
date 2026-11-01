"""Mocked voice-endpoint regressions; no live Groq API or MySQL is required."""
from __future__ import annotations

import io
import httpx
import json
import os
import sys
import types
import unittest
from datetime import date, timedelta
from unittest.mock import patch
from uuid import uuid4

# This runner image may omit mysql-connector-python even though it is a declared app dependency.
# Stub only the import surface so endpoint logic can be tested without any database access.
try:
    import mysql.connector  # noqa: F401
except ModuleNotFoundError:
    mysql_package = types.ModuleType("mysql")
    mysql_package.__path__ = []
    connector_module = types.ModuleType("mysql.connector")

    class ConnectorError(Exception):
        pass

    def unavailable_connect(**kwargs):
        raise ConnectorError("MySQL is intentionally unavailable in the offline test environment")

    connector_module.Error = ConnectorError
    connector_module.connect = unavailable_connect
    mysql_package.connector = connector_module
    sys.modules.setdefault("mysql", mysql_package)
    sys.modules.setdefault("mysql.connector", connector_module)

from fastapi import HTTPException
from starlette.datastructures import Headers, UploadFile
import app as nova


class DeterministicConfirmationEndpointTests(unittest.IsolatedAsyncioTestCase):
    async def test_plain_confirm_bypasses_groq_and_calls_confirmation_tool(self):
        code = "NOVA-C4545574"
        summary = (f"Booking is pending. Code {code}, room 101, check-in 27 Oct 2026, "
                   "check-out 28 Oct 2026, guests 2, name Ajay Maliya, mobile 9887076292, "
                   "total ₹2499.0. Should I confirm this booking?")
        history = json.dumps([{"role": "assistant", "content": summary}])
        with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}), \
             patch.object(nova, "_execute_hotel_tool", return_value={
                 "ok": True, "booking": {"booking_code": code, "room_number": "101", "total_price": 2499.0}
             }) as confirm_mock:
            response = await nova.voice_turn(message="confirm", history=history, language="en", mode="booking", client_turn_id="confirm-test-1")
        self.assertIn("Booking confirmed", response["reply"])
        self.assertEqual(response["provider"], "deterministic-confirmation")
        confirm_mock.assert_called_once()
        self.assertEqual(confirm_mock.call_args.args[0], "confirm_hotel_booking")
        self.assertEqual(confirm_mock.call_args.args[1], {
            "booking_code": code, "guest_name": "Ajay Maliya", "phone": "9887076292"
        })


class DeterministicConfirmationExtractionTests(unittest.TestCase):
    def test_extracts_identity_from_pending_summary(self):
        history = [{"role": "assistant", "content": (
            "Booking is pending. Code NOVA-C4545574, room 101, check-in 27 Oct 2026, "
            "check-out 28 Oct 2026, guests 2, name Ajay Maliya, mobile 9887076292, "
            "total ₹2499.0. Should I confirm this booking?"
        )}]
        self.assertEqual(nova._extract_pending_confirmation_arguments(history), {
            "booking_code": "NOVA-C4545574", "guest_name": "Ajay Maliya", "phone": "9887076292"
        })

    def test_does_not_extract_from_non_confirmation_or_non_pending_message(self):
        self.assertIsNone(nova._extract_pending_confirmation_arguments([
            {"role": "assistant", "content": "Booking confirmed. Code NOVA-C4545574."}
        ]))
        self.assertIsNone(nova._extract_pending_confirmation_arguments([
            {"role": "assistant", "content": "Should I confirm this booking?"}
        ]))


class ConfirmationSummaryValidationTests(unittest.TestCase):
    def test_large_integer_total_in_decimal_format_is_recognized(self):
        check_in = date(2026, 10, 26)
        check_out = date(2027, 10, 27)
        text = (
            "Booking is pending. Code NOVA-2392BDAA, room 201, check-in 26 Oct 2026, "
            "check-out 27 Oct 2027, guests 2, name Ajay Maliya, mobile 9887076292, "
            "total ₹1463634.0. Should I confirm this booking?"
        )
        missing = nova._booking_confirmation_missing_details(
            text, room_number="201", check_in=check_in, check_out=check_out,
            guests=2, price_per_night="3999", guest_name="Ajay Maliya", phone="9887076292",
        )
        self.assertNotIn("total price", missing)
        self.assertEqual(missing, [])

    def test_confirm_tool_accepts_large_total_and_guests_before_number_format(self):
        check_in = date(2026, 10, 26)
        check_out = date(2027, 10, 27)
        summary = (
            "Booking is pending. Code NOVA-2392BDAA, room 201, check-in 26 Oct 2026, "
            "check-out 27 Oct 2027, guests 2, name Ajay Maliya, mobile 9887076292, "
            "total ₹1463634.0. Should I confirm this booking?"
        )
        pending = {
            "booking_code": "NOVA-2392BDAA", "status": "pending_confirmation", "room_number": "201",
            "check_in": check_in, "check_out": check_out, "guests": 2, "total_price": "1463634.00",
        }
        with patch.object(nova, "list_bookings", return_value={"bookings": [pending]}), \
             patch.object(nova, "confirm_pending_booking", return_value={"ok": True, "booking": {"booking_code": "NOVA-2392BDAA"}}) as confirm:
            result = nova._execute_hotel_tool_uncached(
                "confirm_hotel_booking",
                {"booking_code": "NOVA-2392BDAA", "guest_name": "Ajay Maliya", "phone": "9887076292"},
                mode="booking", transcript="confirm", history=[{"role": "assistant", "content": summary}],
            )
        self.assertTrue(result["ok"], result)
        confirm.assert_called_once_with("NOVA-2392BDAA", "Ajay Maliya", "9887076292")

    def test_unusually_long_stay_requires_confirmation_first(self):
        history = [{"role": "assistant", "content": "This is a 366-night stay. Did you mean 27 Oct 2027? Please confirm these dates."}]
        self.assertFalse(nova._long_stay_was_confirmed("confirm", []))
        self.assertFalse(nova._long_stay_was_confirmed("no, I meant 27 Oct 2026", history))
        self.assertTrue(nova._long_stay_was_confirmed("yes, that's correct", history))

    def test_comma_formatted_total_is_recognized(self):
        check_in = date(2026, 10, 26)
        check_out = date(2027, 10, 27)
        text = (
            "Room 201 for 2 guests, check-in 26 Oct 2026, check-out 27 Oct 2027, "
            "guest name Ajay Maliya, mobile 9887076292, total price ₹14,63,634.0. "
            "Should I book this reservation?"
        )
        missing = nova._booking_confirmation_missing_details(
            text, room_number="201", check_in=check_in, check_out=check_out,
            guests=2, price_per_night="3999", guest_name="Ajay Maliya", phone="9887076292",
        )
        self.assertEqual(missing, [])


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.text = json.dumps(payload, ensure_ascii=False)

    def json(self):
        return self._payload


class FakeGroqClient:
    def __init__(self, transcript, chat_payloads):
        self.transcript = transcript
        self.chat_payloads = list(chat_payloads)
        self.requests = []

    async def post(self, url, **kwargs):
        self.requests.append((url, kwargs))
        if url.endswith("/audio/transcriptions"):
            return FakeResponse({"text": self.transcript})
        if url.endswith("/chat/completions"):
            if not self.chat_payloads:
                raise AssertionError("Unexpected extra LLM request")
            return FakeResponse(self.chat_payloads.pop(0))
        raise AssertionError(f"Unexpected URL: {url}")


def booking_confirmation_prompt(check_in, check_out, *, room_number="101", guests=2, price_per_night=2499):
    total = price_per_night * (check_out - check_in).days
    return (
        f"Room {room_number} for {guests} guests, check-in {check_in.strftime('%d %b %Y')}, "
        f"check-out {check_out.strftime('%d %b %Y')}, guest name Ajay Maliya, mobile 9876543210, "
        f"total price ₹{total:,}. Should I book this reservation?"
    )


async def run_voice(client, transcript_history, *, mode="booking", turn_id=None, language="en"):
    nova.app.state.groq_client = client
    audio = UploadFile(
        file=io.BytesIO(b"mock audio payload for endpoint regression"),
        filename="test.webm",
        headers=Headers({"content-type": "audio/webm"}),
    )
    with patch.dict(os.environ, {"GROQ_API_KEY": "test-groq-key"}):
        return await nova.voice_turn(
            audio=audio,
            language=language,
            history=json.dumps(transcript_history, ensure_ascii=False),
            mode=mode,
            client_turn_id=turn_id or f"test-{uuid4()}",
        )


async def run_text(client, message, transcript_history, *, mode="booking", turn_id=None, language="en"):
    nova.app.state.groq_client = client
    with patch.dict(os.environ, {"GROQ_API_KEY": "test-groq-key"}):
        return await nova.voice_turn(
            audio=None,
            message=message,
            language=language,
            history=json.dumps(transcript_history, ensure_ascii=False),
            mode=mode,
            client_turn_id=turn_id or f"typed-{uuid4()}",
        )


class VoiceEndpointTests(unittest.IsolatedAsyncioTestCase):
    async def test_chat_route_is_registered_and_reuses_same_agent(self):
        paths = {route.path for route in nova.app.routes}
        self.assertIn("/api/chat", paths)
        self.assertIn("/api/voice", paths)

    async def test_chat_http_endpoint_accepts_typed_form(self):
        client = FakeGroqClient("should never be used", [{"choices": [{"message": {"role": "assistant", "content": "What dates would you like to stay?"}}]}])
        nova.app.state.groq_client = client
        with patch.dict(os.environ, {"GROQ_API_KEY": "test-groq-key"}):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=nova.app), base_url="http://test") as web_client:
                response = await web_client.post("/api/chat", data={
                    "message": "I want to book a hotel room", "language": "en", "history": "[]",
                    "mode": "booking", "client_turn_id": f"typed-http-{uuid4()}",
                })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["input_mode"], "text")
        self.assertIn("dates", response.json()["reply"].lower())
        self.assertFalse(any(url.endswith("/audio/transcriptions") for url, _ in client.requests))
        self.assertEqual(sum(url.endswith("/chat/completions") for url, _ in client.requests), 1)

    async def test_typed_booking_message_skips_transcription(self):
        client = FakeGroqClient("should never be used", [{"choices": [{"message": {"role": "assistant", "content": "What dates would you like to stay?"}}]}])
        result = await run_text(client, "I want to book a hotel room", [])
        self.assertEqual(result["input_mode"], "text")
        self.assertEqual(result["transcript"], "I want to book a hotel room")
        self.assertIn("dates", result["reply"].lower())
        self.assertEqual(result["latency_ms"]["transcription_ms"], 0.0)
        self.assertEqual(len([url for url, _ in client.requests if url.endswith("/audio/transcriptions")]), 0)
        chat_requests = [kwargs for url, kwargs in client.requests if url.endswith("/chat/completions")]
        self.assertEqual(len(chat_requests), 1)
        self.assertTrue(chat_requests[0]["json"]["tools"])

    async def test_typed_confirmation_executes_existing_booking_tool(self):
        check_in = date.today() + timedelta(days=5)
        check_out = check_in + timedelta(days=2)
        arguments = {
            "guest_name": "Ajay Maliya", "phone": "9876543210",
            "room_number": "101", "check_in": check_in.isoformat(), "check_out": check_out.isoformat(),
            "guests": 2, "special_requests": "",
        }
        tool_call = {
            "id": "typed-booking-confirmation", "type": "function",
            "function": {"name": "create_hotel_booking", "arguments": json.dumps(arguments)},
        }
        client = FakeGroqClient("not used for typed messages", [{"choices": [{"message": {"role": "assistant", "tool_calls": [tool_call]}}]}])
        history = [
            {"role": "user", "content": "I want to book a hotel room"},
            {"role": "assistant", "content": booking_confirmation_prompt(check_in, check_out)},
        ]
        room = {"id": 1, "room_number": "101", "room_type": "Standard Queen", "price_per_night": 2499, "capacity": 2}
        booking = {
            "booking_code": "NOVA-TEXT1234", "room_number": "101", "room_type": "Standard Queen",
            "check_in": check_in.isoformat(), "check_out": check_out.isoformat(), "total_price": 4998,
        }
        with patch.object(nova, "list_rooms", return_value={"rooms": [room], "count": 1}), \
             patch.object(nova, "create_booking", return_value={"message": "ok", "booking": booking}) as create_mock:
            result = await run_text(client, "yes", history)
        create_mock.assert_called_once()
        self.assertEqual(result["input_mode"], "text")
        self.assertIn("NOVA-TEXT1234", result["reply"])
        self.assertEqual([item["tool"] for item in result["tools_called"]], ["create_hotel_booking"])
        self.assertFalse(any(url.endswith("/audio/transcriptions") for url, _ in client.requests))

    async def test_typed_hindi_date_followup_keeps_booking_context(self):
        client = FakeGroqClient("should never be used", [{"choices": [{"message": {"role": "assistant", "content": "Please tell me the check-out date."}}]}])
        history = [
            {"role": "user", "content": "I want to book a hotel room"},
            {"role": "assistant", "content": "Please tell me the check-in date."},
        ]
        result = await run_text(client, "२६ अक्टूबर २०२६", history, language="hi")
        self.assertEqual(result["input_mode"], "text")
        self.assertNotIn("out_of_scope", result)
        chat_requests = [kwargs for url, kwargs in client.requests if url.endswith("/chat/completions")]
        self.assertEqual(len(chat_requests), 1)
        self.assertIn("२६ अक्टूबर २०२६", chat_requests[0]["json"]["messages"][-1]["content"])
        self.assertEqual(len([url for url, _ in client.requests if url.endswith("/audio/transcriptions")]), 0)

    async def test_typed_unrelated_request_is_rejected_without_llm_call(self):
        client = FakeGroqClient("should never be used", [])
        result = await run_text(client, "Write a poem about rain", [])
        self.assertTrue(result["out_of_scope"])
        self.assertEqual(result["input_mode"], "text")
        self.assertEqual(client.requests, [])

    async def test_hindi_date_followup_reaches_function_calling(self):
        client = FakeGroqClient("२६ अक्टूबर २०२६", [{"choices": [{"message": {"role": "assistant", "content": "कृपया चेक-आउट की तारीख बताइए।"}}]}])
        history = [
            {"role": "user", "content": "होटल बुक करने हैं"},
            {"role": "assistant", "content": "कृपया चेक-इन की तारीख बताइए।"},
        ]
        result = await run_voice(client, history, language="hi")
        self.assertNotIn("out_of_scope", result)
        self.assertEqual(result["transcript"], "२६ अक्टूबर २०२६")
        self.assertIn("चेक-आउट", result["reply"])
        chat_requests = [kwargs for url, kwargs in client.requests if url.endswith("/chat/completions")]
        self.assertEqual(len(chat_requests), 1)
        self.assertTrue(chat_requests[0]["json"]["tools"])
        self.assertIn("Current date in Asia/Kolkata", chat_requests[0]["json"]["messages"][0]["content"])
        self.assertIn("transcription_ms", result["latency_ms"])
        self.assertIn("chat_ms_total", result["latency_ms"])
        self.assertGreaterEqual(result["latency_ms"]["chat_calls"], 1)

    async def test_multiple_create_tool_calls_execute_only_one_booking(self):
        check_in = date.today() + timedelta(days=5)
        check_out = check_in + timedelta(days=2)
        arguments = {
            "guest_name": "Ajay Maliya",
            "phone": "9876543210",
            "room_number": "101",
            "check_in": check_in.isoformat(),
            "check_out": check_out.isoformat(),
            "guests": 2,
            "special_requests": "",
        }
        call = {
            "type": "function",
            "function": {"name": "create_hotel_booking", "arguments": json.dumps(arguments)},
        }
        tool_call_message = {
            "role": "assistant",
            "tool_calls": [dict(call, id="call-one"), dict(call, id="call-two")],
        }
        client = FakeGroqClient("yes", [{"choices": [{"message": tool_call_message}]}])
        history = [
            {"role": "user", "content": "Book a hotel room"},
            {"role": "assistant", "content": booking_confirmation_prompt(check_in, check_out)},
        ]
        room = {"id": 1, "room_number": "101", "room_type": "Standard Queen", "price_per_night": 2499, "capacity": 2}
        booking = {
            "booking_code": "NOVA-TEST1234", "room_number": "101", "room_type": "Standard Queen",
            "check_in": check_in.isoformat(), "check_out": check_out.isoformat(), "total_price": 4998,
        }
        turn_id = f"duplicate-tool-{uuid4()}"
        with patch.object(nova, "list_rooms", return_value={"rooms": [room], "count": 1}), \
             patch.object(nova, "create_booking", return_value={"message": "ok", "booking": booking}) as create_mock:
            result = await run_voice(client, history, turn_id=turn_id)

        create_mock.assert_called_once()
        self.assertIn("NOVA-TEST1234", result["reply"])
        self.assertEqual(len(result["tools_called"]), 1)
        self.assertEqual(result["tools_called"][0]["tool"], "create_hotel_booking")
        self.assertEqual(result["latency_ms"]["tool_calls"], 1)

    async def test_failed_booking_cannot_be_reported_as_success(self):
        check_in = date.today() + timedelta(days=5)
        check_out = check_in + timedelta(days=2)
        arguments = {
            "guest_name": "Ajay Maliya", "phone": "9876543210",
            "room_number": "101", "check_in": check_in.isoformat(), "check_out": check_out.isoformat(),
            "guests": 2, "special_requests": "",
        }
        tool_call_message = {
            "role": "assistant",
            "tool_calls": [{
                "id": "call-failed-create", "type": "function",
                "function": {"name": "create_hotel_booking", "arguments": json.dumps(arguments)},
            }],
        }
        client = FakeGroqClient("yes", [
            {"choices": [{"message": tool_call_message}]},
            {"choices": [{"message": {"role": "assistant", "content": "Your booking is confirmed. Code NOVA-FAKE1234."}}]},
        ])
        room = {"id": 1, "room_number": "101", "room_type": "Standard Queen", "price_per_night": 2499, "capacity": 2}
        history = [
            {"role": "user", "content": "Book a hotel room"},
            {"role": "assistant", "content": booking_confirmation_prompt(check_in, check_out)},
        ]
        with patch.object(nova, "list_rooms", return_value={"rooms": [room], "count": 1}), \
             patch.object(nova, "create_booking", side_effect=HTTPException(503, "database unavailable")) as create_mock:
            result = await run_voice(client, history)
        create_mock.assert_called_once()
        self.assertNotIn("NOVA-FAKE1234", result["reply"])
        self.assertIn("couldn't complete", result["reply"].lower())

    async def test_booking_tool_rejects_details_that_differ_from_confirmation(self):
        check_in = date.today() + timedelta(days=5)
        check_out = check_in + timedelta(days=2)
        arguments = {
            "guest_name": "Ajay Maliya", "phone": "9876543210",
            "room_number": "101", "check_in": check_in.isoformat(), "check_out": check_out.isoformat(),
            "guests": 2, "special_requests": "",
        }
        room = {"id": 1, "room_number": "101", "room_type": "Standard Queen", "price_per_night": 2499, "capacity": 2}
        history = [{"role": "assistant", "content": booking_confirmation_prompt(check_in, check_out, room_number="201")}]
        with patch.object(nova, "list_rooms", return_value={"rooms": [room], "count": 1}), \
             patch.object(nova, "create_booking", return_value={"booking": {"status": "pending_confirmation"}}) as create_mock:
            result = nova._execute_hotel_tool_uncached(
                "create_hotel_booking", arguments, mode="booking", transcript="room 101", history=history,
            )
        create_mock.assert_called_once()
        self.assertEqual(create_mock.call_args.kwargs["initial_status"], "pending_confirmation")
        self.assertTrue(result["ok"])
        self.assertTrue(result["pending_confirmation"])

    async def test_confirmation_tool_updates_only_after_complete_summary_and_yes(self):
        check_in = date.today() + timedelta(days=5)
        check_out = check_in + timedelta(days=2)
        code = "NOVA-AB1234"
        summary = (f"Booking is pending. Code {code}, room 201, check-in {check_in.isoformat()}, "
                   f"check-out {check_out.isoformat()}, 2 guests, name Ajay Maliya, mobile 9876543210, "
                   f"total price ₹7998. Should I confirm this booking?")
        row = {"status": "pending_confirmation", "booking_code": code, "room_number": "201",
               "check_in": check_in.isoformat(), "check_out": check_out.isoformat(), "guests": 2,
               "guest_name": "Ajay Maliya", "phone": "9876543210", "total_price": 7998}
        with patch.object(nova, "list_bookings", return_value={"bookings": [row]}), \
             patch.object(nova, "confirm_pending_booking", return_value={"booking": {"status": "confirmed", "booking_code": code}}) as confirm_mock:
            result = nova._execute_hotel_tool_uncached(
                "confirm_hotel_booking", {"booking_code": code, "guest_name": "Ajay Maliya", "phone": "9876543210"},
                mode="booking", transcript="Yes, confirm.", history=[{"role": "assistant", "content": summary}],
            )
        self.assertTrue(result["ok"])
        confirm_mock.assert_called_once_with(code, "Ajay Maliya", "9876543210")

    async def test_cancel_tool_rejects_unread_confirmation_code(self):
        history = [{"role": "assistant", "content": "Should I cancel booking NOVA-OTHER1234 for room 101?"}]
        with patch.object(nova, "cancel_booking") as cancel_mock:
            result = nova._execute_hotel_tool_uncached(
                "cancel_hotel_booking", {"booking_code": "NOVA-AB1234", "guest_name": "Ajay Maliya", "phone": "9876543210"},
                mode="cancel", transcript="yes", history=history,
            )
        cancel_mock.assert_not_called()
        self.assertFalse(result["ok"])
        self.assertTrue(result.get("confirmation_required"))

    async def test_cancel_tool_accepts_exact_read_back_code_after_yes(self):
        code = "NOVA-AB1234"
        history = [{"role": "assistant", "content": f"Room 101, booking code {code}, check-in 26 Oct 2026, check-out 28 Oct 2026. Should I cancel this booking?"}]
        with patch.object(nova, "cancel_booking", return_value={"booking_code": code, "status": "cancelled"}) as cancel_mock:
            result = nova._execute_hotel_tool_uncached(
                "cancel_hotel_booking", {"booking_code": code, "guest_name": "Ajay Maliya", "phone": "9876543210"},
                mode="cancel", transcript="yes", history=history,
            )
        cancel_mock.assert_called_once_with(booking_code=code, guest_name="Ajay Maliya", phone="9876543210")
        self.assertTrue(result["ok"])

    async def test_cancel_tool_rejects_negation_even_when_prompted(self):
        history = [{"role": "assistant", "content": "Should I cancel this booking?"}]
        with patch.object(nova, "cancel_booking") as cancel_mock:
            result = nova._execute_hotel_tool_uncached(
                "cancel_hotel_booking", {"booking_code": "NOVA-AB1234", "guest_name": "Ajay Maliya", "phone": "9876543210"},
                mode="cancel", transcript="No, don't cancel it", history=history,
            )
        cancel_mock.assert_not_called()
        self.assertFalse(result["ok"])
        self.assertTrue(result.get("confirmation_required"))

    async def test_idempotency_cache_reuses_side_effect_result(self):
        turn_id = f"same-turn-{uuid4()}"
        with patch.object(nova, "_execute_hotel_tool_uncached", return_value={"ok": True, "booking_code": "NOVA-CACHED"}) as inner:
            first = nova._execute_hotel_tool(
                "cancel_hotel_booking", {"booking_code": "NOVA-CACHED", "guest_name": "Ajay Maliya", "phone": "9876543210"},
                mode="cancel", transcript="yes", history=[{"role": "assistant", "content": "Should I cancel this booking?"}], client_turn_id=turn_id,
            )
            second = nova._execute_hotel_tool(
                "cancel_hotel_booking", {"booking_code": "NOVA-CACHED", "guest_name": "Ajay Maliya", "phone": "9876543210"},
                mode="cancel", transcript="yes", history=[{"role": "assistant", "content": "Should I cancel this booking?"}], client_turn_id=turn_id,
            )
        inner.assert_called_once()
        self.assertEqual(first, second)
        self.assertEqual(second["booking_code"], "NOVA-CACHED")


if __name__ == "__main__":
    unittest.main()
