from services.catalog import SERVICES, detect_service
from nodes.router import decide

# ── Shared idle state ──────────────────────────────────────────────────────────
IDLE = {"mode": "conversational", "intake_step": "identify", "current_field": None}


# ── Dental router tests ────────────────────────────────────────────────────────

def test_book_starts_intake():
    assert decide(dict(IDLE), "I'd like to book an appointment") == "start_intake"


def test_emergency_word_starts_intake_from_idle():
    assert decide(dict(IDLE), "I have a terrible toothache") == "start_intake"


def test_question_stays_rag():
    assert decide(dict(IDLE), "Does whitening damage enamel?") == "rag"


def test_midflow_question_resumes():
    state = {"mode": "transactional", "intake_step": "collect", "current_field": "phone"}
    assert decide(state, "wait, do you take walk-ins?") == "answer_then_resume"


def test_midflow_value_collects():
    state = {"mode": "transactional", "intake_step": "collect", "current_field": "phone"}
    assert decide(state, "09171234567") == "collect"


# ── Service catalog tests ──────────────────────────────────────────────────────

def test_detect_service_by_keyword():
    assert detect_service("i need a cleaning") == "cleaning"
    assert detect_service("my tooth is killing me") == "emergency"
    assert detect_service("teeth whitening please") == "whitening"
    assert detect_service("just a checkup consult") == "consultation"


def test_detect_service_checkup_only_is_cleaning():
    """Bare checkup without consult keywords resolves to cleaning."""
    assert detect_service("book me a checkup") == "cleaning"


def test_detect_service_none_for_unrelated():
    assert detect_service("what are your hours?") is None


def test_catalog_has_four_services():
    assert set(SERVICES) == {"cleaning", "consultation", "whitening", "emergency"}


def test_emergency_wins_when_cooccurring():
    """Emergency is checked first, so it wins even when cosmetic keywords co-occur."""
    assert detect_service("chipped tooth whitening") == "emergency"
    assert detect_service("toothache after a cleaning") == "emergency"


def test_consulting_is_not_consultation():
    """Word-boundary matching prevents 'consult' from matching 'consulting'."""
    assert detect_service("I work at a consulting firm") is None


# ── P2 vs P3 word-boundary boundary tests ─────────────────────────────────────

def test_p2_does_not_hijack_pending_field_on_substring():
    """'book' inside 'facebook_user' must not fire P2 while a field is pending."""
    state = {"mode": "transactional", "intake_step": "collect", "current_field": "phone"}
    assert decide(state, "my handle is facebook_user") == "collect"


def test_p2_explicit_booking_still_wins_midflow():
    """A genuine mid-intake service-switch ('book') must still route to start_intake."""
    state = {"mode": "transactional", "intake_step": "collect", "current_field": "phone"}
    assert decide(state, "actually let me book a whitening instead") == "start_intake"


def test_booking_word_starts_intake():
    """The inflected form 'booking' (listed explicitly) must trigger start_intake."""
    assert decide({"mode": "conversational", "intake_step": "identify", "current_field": None}, "I need a booking for next week") == "start_intake"


def test_unavailable_does_not_start_intake():
    """'unavailable' must not match the 'available' hint due to word-boundary anchoring."""
    assert decide({"mode": "conversational", "intake_step": "identify", "current_field": None}, "the dentist was unavailable last time I came by") == "rag"


# ── P3b: booked-state echo rule ────────────────────────────────────────────────

_BOOKED = {"mode": "conversational", "intake_step": "booked", "current_field": None}


def test_booked_plus_affirm_routes_to_confirm():
    """P3b: booked state + plain affirmation → confirm (idempotency short-circuit)."""
    assert decide(dict(_BOOKED), "accept") == "confirm"
    assert decide(dict(_BOOKED), "yes") == "confirm"
    assert decide(dict(_BOOKED), "ok") == "confirm"


def test_booked_plus_affirm_question_falls_to_rag():
    """P3b must not fire when the message contains '?' — question goes to rag.

    Note: messages that also contain booking-intent keywords (e.g. 'booking')
    are caught earlier by P2 (start_intake), which is correct behaviour.
    """
    assert decide(dict(_BOOKED), "accept?") == "rag"
    assert decide(dict(_BOOKED), "am I confirmed?") == "rag"


def test_booked_plain_statement_goes_to_rag():
    """A message that is neither an affirmation nor a booking keyword → rag when booked."""
    assert decide(dict(_BOOKED), "thanks, that's great") == "rag"


# ── Post-booking CTA router unit tests (Issues 1, 2, 3) ──────────────────────

def test_booked_restart_routes_to_confirm():
    """Issue 1 fix: P1 fires when intake_step == 'booked' even at mode='conversational'.

    The success message advertises 'restart' as a CTA, so the router must honour
    it from the terminal booked state.
    """
    assert decide(dict(_BOOKED), "restart") == "confirm"


def test_booked_adjust_routes_to_confirm():
    """Issue 3 fix: P3b now matches ADJUST_HINTS (without '?') at booked state.

    confirm.py has a booked+adjust branch that emits the 'already booked' nudge,
    but the router was previously sending 'adjust' to rag. Fixed by extending P3b.
    """
    assert decide(dict(_BOOKED), "adjust") == "confirm"


def test_booked_adjust_question_falls_to_rag():
    """P3b '?' guard still applies: 'can I adjust?' must NOT route to confirm."""
    assert decide(dict(_BOOKED), "can I adjust?") == "rag"
