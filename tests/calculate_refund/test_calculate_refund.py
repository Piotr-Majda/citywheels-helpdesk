"""Template tests for refund rules and time boundaries."""

import pytest


class TestCalculateRefund:
    @pytest.mark.skip(reason="TODO: implement refund calculation and its assertions")
    def test_full_refund(self):
        """CW-1001: 40 EUR rental plus 50 EUR deposit equals 90 EUR."""

    @pytest.mark.skip(reason="TODO: implement refund calculation and its assertions")
    def test_half_refund(self):
        """CW-1002: 40 EUR rental plus 300 EUR deposit equals 340 EUR."""

    @pytest.mark.skip(reason="TODO: implement refund calculation and its assertions")
    def test_deposit_only(self):
        """CW-1003: only the 50 EUR deposit is refundable."""

    @pytest.mark.skip(reason="TODO: implement refund calculation and its assertions")
    def test_exactly_48_hours(self):
        """CW-1007: full rental refund, total 186 EUR."""

    @pytest.mark.skip(reason="TODO: implement refund calculation and its assertions")
    def test_exactly_24_hours(self):
        """CW-1010: half rental refund, total 170 EUR."""

    @pytest.mark.skip(reason="TODO: implement refund calculation and its assertions")
    def test_non_confirmed_bookings(self):
        """Cancelled, completed, and in-progress bookings cannot be cancelled."""

    @pytest.mark.skip(reason="TODO: implement refund calculation and its assertions")
    def test_voucher_refund(self):
        """CW-1004: rental refund is a voucher; deposit follows its payment method."""

    @pytest.mark.skip(reason="TODO: implement refund calculation and its assertions")
    def test_unknown_booking(self):
        """An unknown booking returns not_found without crashing."""
