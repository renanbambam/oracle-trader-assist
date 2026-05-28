"""Unit tests for Symbol value object."""

from oracle.domain.market.value_objects import Symbol


class TestNormalization:
    def test_lowercase_uppercased(self):
        assert Symbol(value="petr4").value == "PETR4"

    def test_mixed_case_uppercased(self):
        assert Symbol(value="WinFut").value == "WINFUT"

    def test_leading_trailing_whitespace_stripped(self):
        assert Symbol(value="  PETR4  ").value == "PETR4"

    def test_lowercase_with_whitespace(self):
        assert Symbol(value="  petr4  ").value == "PETR4"

    def test_str_returns_normalized_value(self):
        assert str(Symbol(value="petr4")) == "PETR4"
