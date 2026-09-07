"""Money, booking state machine, and dashboard anonymity — the rules that cost
real money or real trust when they are wrong."""
from __future__ import annotations

import pytest

from app.config import settings
from app.models import BookingStatus
from app.routers.bookings import ALLOWED_TRANSITIONS
from app.routers.dashboard import suppress
from app.schemas import THOUSANDS_SEPARATOR, Money, format_dzd

NBSP = THOUSANDS_SEPARATOR  # U+202F — see schemas.format_dzd


# --------------------------------------------------------------------------- #
# Money
# --------------------------------------------------------------------------- #
def test_format_dzd_groups_thousands_with_a_narrow_no_break_space():
    assert format_dzd(320000) == f"3{NBSP}200,00 DZD"
    assert format_dzd(1150000) == f"11{NBSP}500,00 DZD"


def test_format_dzd_keeps_centimes_visible():
    assert format_dzd(1) == "0,01 DZD"
    assert format_dzd(199) == "1,99 DZD"


def test_format_dzd_handles_zero_and_refunds():
    assert format_dzd(0) == "0,00 DZD"
    assert format_dzd(-450000) == f"-4{NBSP}500,00 DZD"


def test_money_multiplication_stays_exact():
    # The float trap this design exists to avoid: 3200.00 * 3 must be 9600.00.
    unit = 320000
    assert Money.of(unit * 3).display == f"9{NBSP}600,00 DZD"


# --------------------------------------------------------------------------- #
# Booking state machine
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "source,target",
    [
        (BookingStatus.pending, BookingStatus.confirmed),
        (BookingStatus.pending, BookingStatus.cancelled),
        (BookingStatus.confirmed, BookingStatus.completed),
        (BookingStatus.confirmed, BookingStatus.cancelled),
    ],
)
def test_legal_booking_transitions(source, target):
    assert target in ALLOWED_TRANSITIONS[source]


@pytest.mark.parametrize(
    "source,target",
    [
        (BookingStatus.cancelled, BookingStatus.confirmed),
        (BookingStatus.completed, BookingStatus.cancelled),
        (BookingStatus.completed, BookingStatus.confirmed),
        (BookingStatus.pending, BookingStatus.completed),
    ],
)
def test_illegal_booking_transitions_are_refused(source, target):
    # Notably: a cancelled booking can never come back to life, and a booking
    # cannot be completed without first being confirmed.
    assert target not in ALLOWED_TRANSITIONS[source]


def test_terminal_states_have_no_exits():
    assert ALLOWED_TRANSITIONS[BookingStatus.cancelled] == set()
    assert ALLOWED_TRANSITIONS[BookingStatus.completed] == set()


# --------------------------------------------------------------------------- #
# Dashboard anonymity
# --------------------------------------------------------------------------- #
def test_small_cohorts_are_withheld_not_rounded():
    assert suppress(3, cohort=3) is None
    assert suppress(1200, cohort=settings.min_cohort - 1) is None


def test_large_cohorts_report_the_true_value():
    assert suppress(1200, cohort=settings.min_cohort) == 1200


def test_a_single_visitor_can_never_be_reported():
    assert suppress(1, cohort=1) is None
