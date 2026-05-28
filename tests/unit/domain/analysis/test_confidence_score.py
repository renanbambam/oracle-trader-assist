"""Unit tests for ConfidenceScore value object."""

import pytest
from pydantic import ValidationError

from oracle.domain.analysis.enums import ConfidenceLabel
from oracle.domain.analysis.value_objects import ConfidenceScore

_J = "test justification"


class TestLabelDerivation:
    """Labels are derived automatically by from_value() from the numeric score."""

    def test_score_100_is_muito_alta(self):
        assert ConfidenceScore.from_value(100.0, _J).label == ConfidenceLabel.MUITO_ALTA

    def test_score_at_85_boundary_is_muito_alta(self):
        assert ConfidenceScore.from_value(85.0, _J).label == ConfidenceLabel.MUITO_ALTA

    def test_score_90_is_muito_alta(self):
        assert ConfidenceScore.from_value(90.0, _J).label == ConfidenceLabel.MUITO_ALTA

    def test_score_just_below_85_is_alta(self):
        assert ConfidenceScore.from_value(84.9, _J).label == ConfidenceLabel.ALTA

    def test_score_at_70_boundary_is_alta(self):
        assert ConfidenceScore.from_value(70.0, _J).label == ConfidenceLabel.ALTA

    def test_score_just_below_70_is_moderada(self):
        assert ConfidenceScore.from_value(69.9, _J).label == ConfidenceLabel.MODERADA

    def test_score_at_50_boundary_is_moderada(self):
        assert ConfidenceScore.from_value(50.0, _J).label == ConfidenceLabel.MODERADA

    def test_score_just_below_50_is_baixa(self):
        assert ConfidenceScore.from_value(49.9, _J).label == ConfidenceLabel.BAIXA

    def test_score_at_30_boundary_is_baixa(self):
        assert ConfidenceScore.from_value(30.0, _J).label == ConfidenceLabel.BAIXA

    def test_score_just_below_30_is_muito_baixa(self):
        assert ConfidenceScore.from_value(29.9, _J).label == ConfidenceLabel.MUITO_BAIXA

    def test_score_0_is_muito_baixa(self):
        assert ConfidenceScore.from_value(0.0, _J).label == ConfidenceLabel.MUITO_BAIXA


class TestScoreRounding:
    def test_score_is_rounded_to_1_decimal(self):
        cs = ConfidenceScore.from_value(75.123, _J)
        assert cs.score == 75.1

    def test_score_already_1_decimal_unchanged(self):
        cs = ConfidenceScore.from_value(72.5, _J)
        assert cs.score == 72.5


class TestValidation:
    def test_score_above_100_raises(self):
        with pytest.raises(ValidationError):
            ConfidenceScore(score=100.1, label=ConfidenceLabel.MUITO_ALTA, justification=_J)

    def test_score_below_0_raises(self):
        with pytest.raises(ValidationError):
            ConfidenceScore(score=-0.1, label=ConfidenceLabel.MUITO_BAIXA, justification=_J)


class TestProperties:
    def test_muito_alta_is_high_conviction(self):
        assert ConfidenceScore.from_value(88.0, _J).is_high_conviction is True

    def test_alta_is_high_conviction(self):
        assert ConfidenceScore.from_value(72.0, _J).is_high_conviction is True

    def test_moderada_is_not_high_conviction(self):
        assert ConfidenceScore.from_value(55.0, _J).is_high_conviction is False

    def test_baixa_is_not_high_conviction(self):
        assert ConfidenceScore.from_value(35.0, _J).is_high_conviction is False

    def test_frozen(self):
        cs = ConfidenceScore.from_value(75.0, _J)
        with pytest.raises(Exception):
            cs.score = 99.0  # type: ignore
