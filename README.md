# Nova — Voice + Text Hotel Booking with Function Calling

Nova has exactly two user-facing workflows: **Hotel Booking** and **Cancel Booking**. Both support voice and typed chat; the selected menu determines which hotel operations the model is allowed to use. You do not need a working microphone or speaker to complete the workflow: type into the conversation box and read Nova’s reply on screen.

## The key architectural fix

The earlier version only sent text to a normal chat completion and used a brittle keyword guard before the model. It did not send `tools` to Groq, so it was **not actually using LLM function calling**. It also could reject a date as unrelated when a user was answering Nova's previous question.

This version sends OpenAI-compatible `tools` definitions to Groq and executes only four allow-listed operations on the server:

- `search_room_availability` — checks actual availability using the MySQL-backed booking service.
- `create_hotel_booking` — creates a real reservation only after explicit confirmation in the latest user turn.
- `find_hotel_bookings` — looks up bookings only by matching guest name and mobile number (optionally narrowed by booking code).
- `cancel_hotel_booking` — cancels only after explicit confirmation in the latest user turn.

The server executes tools directly against the same validated Python booking functions used by the REST API. The LLM cannot execute arbitrary Python, SQL, shell commands, web searches, or other tools. The tool loop is bounded to four model calls to prevent infinite cycles. Tool results are sent back to the model before it speaks, so it should describe actual results rather than invent them.

## Conversation-state fix

The selected menu mode and recent conversation history are sent with every voice or text turn. `/api/voice` transcribes audio and then uses the shared hotel-only agent; `/api/chat` skips transcription and sends the typed message directly to that same agent, tool definitions, flow guards, confirmation checks, and booking service. A new `flow_guard.py` recognizes when Nova asked for a slot, including Hindi prompts such as `चेक-इन दिनांक बताइए`; a short date answer such as `26 अक्टूबर 2026` is therefore treated as a booking follow-up instead of being rejected by the scope guard. Obvious unrelated requests are still rejected locally.

The browser fills visible form fields from spoken dates, guest count, name and mobile number. A single spoken date is assigned according to the latest check-in/check-out prompt; Hindi/Devanagari dates and relative pairs such as “kal se parso tak” are recognized locally for form convenience. Changing dates or guest count clears stale room choices. **The browser does not issue a duplicate availability request while processing a spoken turn**; the server-side availability tool remains authoritative, and the backend tool owns booking/cancellation side effects.

The deterministic scope filter does not classify a booking-code answer as a programming request. Confirmation checks reject common English/Hindi/Hinglish negations, require a matching prior action-specific confirmation prompt, and ignore prior success messages. Before creating a reservation, the server rechecks availability and verifies that the latest confirmation read back the same room number, both dates, guest count, and calculated total price; cancellation likewise requires the exact booking code to have been read back in the latest cancellation prompt. The server processes no more than one state-changing tool call per turn and uses a 15-minute in-process idempotency cache keyed by the client turn ID. This cache protects repeats in one running worker; durable deduplication across restarts/multiple workers is still a production-hardening task.

Per-turn structured logs now include transcription, scope guard, cumulative chat, tool, and total latency. TTS generation logs its own latency and audio size. The booking form and cancellation lookup no longer collect or require email. Existing MySQL databases are migrated by dropping the legacy email column at startup. The browser also uses a guarded microphone-start path, discards empty/noise-only audio, stops recordings at 30 seconds, and avoids starting a pending microphone after the user ends the session.


## Text chat fallback (same Conversation panel)

The `Conversation` card includes a visible text composer directly below the chat history. If microphone permission, speech recognition, or audio playback fails, type the same hotel booking/cancellation request there and press **Send message** (or Enter; use Shift+Enter for a newline). Typed and voice turns call the same `/api/chat` backend and share the current mode's conversation history. There is no separate chat tab to hunt for.

The launcher selects a free port instead of killing another process that might occupy port `8000`, then opens the page only after it detects the new UI build. The home page sends no-cache headers to reduce the risk of seeing an older cached frontend.

## Setup (Windows)

1. Install Python 3.12 and MySQL Server.
2. Extract this ZIP and run `run.bat` once. It installs missing requirements and creates `.env` from `.env.example`. On later launches it checks imports first and skips reinstalling dependencies that are already available.
3. Edit `.env`: set `GROQ_API_KEY` and the `MYSQL_*` credentials. Never share your `.env` or paste your real API key into source code.
4. Create the database and tables. With MySQL Workbench, open `database/schema.sql` and execute the full script. Or, in a terminal where the MySQL client is on PATH, run `mysql -u root -p < database/schema.sql`. The script creates the default `nova_booking` database and demo rooms; if `MYSQL_DATABASE` is different, update the database name in the SQL script too.
5. Run `run.bat` again. It picks an available localhost port (normally `8000`) and opens the correct updated UI automatically; check the URL printed in the console if you need to open it manually. Check that same URL plus `/health`; `database: ready` means the schema connection worked.
6. Choose **Hotel Booking**. Start the voice session and say e.g. “होटल बुक करने हैं”, or type the same request in the Conversation box and press **Send message**. Continue by voice or typing; your check-in/check-out dates, guest count, room, name and mobile number are handled by the same agent. Nova checks availability, reads back the final details on screen (and by voice if voice mode is active), and asks for confirmation before creating a booking.
7. For cancellation, choose **Cancel Booking** and speak or type the guest name and mobile number. Nova shows the matching reservation and asks for explicit confirmation before cancellation. You can read the text reply even when speakers or microphone are unavailable.

## Configuration

- `GROQ_API_KEY`: secret API key, only in `.env`.
- `GROQ_CHAT_MODEL`: defaults to `openai/gpt-oss-20b`; use a Groq model that supports tool/function calling in your account.
- `GROQ_TRANSCRIPTION_MODEL`: defaults to `whisper-large-v3-turbo`.
- `MYSQL_*`: database connection values.

## Checks performed in this environment

- Python syntax compilation passed for `app.py`, `admin_auth.py`, `admin_portal.py`, and `admin_data.py`.
- Admin route/security integration checks passed with an offline MySQL-driver stub: customer `/` remained reachable; `/admin` served the login page; an unauthenticated `/admin/dashboard` redirected to `/admin`; protected data APIs rejected unauthenticated access; login created a session; CSRF-less logout was rejected; CSRF-protected logout succeeded; and the session was revoked afterward.
- Forgot-password/reset tests passed with a mocked Resend HTTP response: the reset email targeted the configured `ADMIN_EMAIL`, the link used the configured base URL, the token was single-use, and the new password could sign in. No real email was sent in this test.
- The supplied Nova test suite ran with an offline MySQL connector stub: 51 passed, 1 failed, and 16 subtests passed. The one failing test is `test_typed_unrelated_request_is_rejected_without_llm_call`; the provided `app.py` currently has the local scope-rejection block commented out, so that existing test expects behavior that this supplied Nova code does not currently enforce. Admin integration did not change the voice/chat decision logic.
- Live MySQL booking reads/writes, live Resend delivery, live Groq requests, microphones and TTS could not be verified in this environment. Install the project requirements and test those integrations locally with your credentials.

## Production security notes

This remains a local development starter. The admin routes now have session authentication, CSRF checks and basic in-process rate limiting, but those controls are not a substitute for a reviewed public deployment. Before public deployment, add shared-store rate limiting/session revocation, trusted-host configuration, audit logging, secret management, database migrations, observability, privacy/retention policy, backups, and automated end-to-end tests. Name + mobile-number lookup is a basic demo check, not sufficient authentication for a public production service. Keep the server bound to localhost for local testing.


## Startup logging fix

The launcher creates the `logs` directory before starting Uvicorn. The application also creates it during import and treats file logging as optional: if Windows permissions or antivirus block the directory, the server continues with console logging instead of crashing with `FileNotFoundError`.

If the same old traceback still appears, stop all running Nova terminals, extract this ZIP into a **new folder**, and run the `run.bat` from that new folder. Confirm `app.py` contains `LOG_DIR.mkdir(parents=True, exist_ok=True)` and the guarded `_log_handlers` block.


## Text chat fallback

The Conversation card includes a text box and **Send message** button. Press Enter to send and Shift+Enter to add a newline. Typed turns use `/api/chat` and skip speech-to-text entirely. They share the same mode-specific conversation history, scope guard, Groq function-calling tools, confirmation requirements, idempotency logic, and MySQL booking/cancellation functions as voice turns. Text replies are rendered on screen without requiring TTS playback. If the microphone is denied or audio playback is unavailable, use this box to continue the workflow.

## Booking confirmation and conversation context (updated)

The chat booking flow now uses a two-step MySQL lifecycle:

1. `create_hotel_booking` stores the reservation with `status='pending_confirmation'` after collecting details and checking availability.
2. Nova reads back the booking code and complete details, then asks one final confirmation question.
3. After an explicit affirmative reply to that summary, `confirm_hotel_booking` verifies the booking code, guest name, mobile number and summary, then calls `confirm_pending_booking()`.
4. `confirm_pending_booking()` opens a transaction, rechecks room/date conflicts, and runs `UPDATE hotel_bookings SET status='confirmed' ...`. Nova only says the booking is confirmed if that database operation succeeds.

At startup, `initialize_booking_database()` upgrades an existing `hotel_bookings.status` enum to include `pending_confirmation`. The equivalent manual migration is `database/migrations/002_pending_booking_confirmation.sql`. Back up the database before running a migration on real reservations.

Conversation context is increased to the latest 40 messages. To limit token usage, each message is capped at 900 characters and generated responses remain capped at 150 tokens.

## Admin portal (integrated into the same Nova app)

The admin portal is integrated as additional routes in the same FastAPI process. It does not replace or edit Nova's Groq voice, chat, booking, cancellation, or customer UI handlers. The customer website stays at `/`; the admin login is at `/admin`; successful login opens `/admin/dashboard`. Admin booking data reuses the existing `MYSQL_*` connection and the existing `hotel_rooms` / `hotel_bookings` tables. Admin credentials and one-time password-reset tokens are stored separately in `data/admin_auth.db` (SQLite).

### Run on Windows

1. Extract the project folder and open `run.bat`. The launcher installs the listed packages if needed and starts Nova on a free localhost port.
2. Open the customer URL printed by the launcher. Admin login is the same URL followed by `/admin` (for example `http://127.0.0.1:8000/admin`).
3. The initial admin email and password are the `ADMIN_EMAIL` and `ADMIN_PASSWORD` values in the root `.env`. The launcher generates a strong persistent `ADMIN_SESSION_SECRET` if one is missing, and the first application start creates the separate local admin-auth database. Change the initial password after signing in and keep `.env` private.
4. Admin dashboard and its data APIs require an authenticated session. The cookie is HttpOnly, SameSite=Lax, scoped to `/admin`, and expires after eight hours. Mutating admin APIs also require a CSRF token. Login, forgot-password and reset endpoints have per-IP in-process rate limits. Passwords are stored with PBKDF2-HMAC-SHA256 hashes; reset links are random, stored only as hashes, expire after 20 minutes, and are single-use. A password reset invalidates existing admin sessions.

### Enable forgot-password email

The supplied ZIP did not contain a Resend API key, and its old email function had a fixed recipient. The integrated version sends the reset email to the active admin account's configured `ADMIN_EMAIL`. The reset-email HTTP request runs in a worker thread so waiting for email delivery does not block Nova's async voice/chat event loop. To enable delivery:

1. Create a Resend API key in your Resend account and put it in root `.env` as `RESEND_API_KEY=re_...`.
2. Set `EMAIL_FROM` to a sender identity authorized in your Resend account. For production delivery, verify a domain in Resend and use a sender address on that verified domain; the Resend dashboard/docs show the sender identities available to your account.
3. Run `run.bat` again. It sets `APP_BASE_URL` to the actual port selected for that run, so reset links use the correct local address.
4. On `/admin`, choose **Forgot password?**, enter the admin email and check its inbox and spam folder. The UI intentionally gives the same response for registered and unregistered emails to avoid account enumeration. Check the server console and Resend dashboard if a message does not arrive.

For a manual run instead of `run.bat`, set `APP_BASE_URL` to the exact base URL (including port) before starting Uvicorn. For public deployment, use a real HTTPS base URL, set `ADMIN_COOKIE_SECURE=true`, use a verified email sender/domain, and keep the app behind HTTPS. Do not expose the local development server directly to the public internet.

### Admin security and scope

- `GET /admin/dashboard` redirects unauthenticated visitors to `/admin`; the `/admin/api/admin/*` reservation APIs are protected independently, so hiding the page alone is not the security boundary.
- Admin logout revokes existing sessions for that admin account.
- The login database is separate from Nova's booking database; the dashboard reads and writes only the existing Nova MySQL booking tables.
- Login throttling is in-process. For a multi-worker/public deployment, move rate limiting and session revocation to a shared store, add a reverse proxy, trusted-host/HTTPS configuration, audit logging, database backups, and deployment-grade monitoring.
- The forgot-password endpoint does not reveal whether an email belongs to an admin account. If Resend is not configured, the request is logged server-side and no message can be delivered until the API key/sender are configured.
