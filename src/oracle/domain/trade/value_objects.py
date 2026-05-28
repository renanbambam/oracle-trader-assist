"""Trade domain — value objects."""

from pydantic import Field, field_validator

from oracle.domain.shared.base import ValueObject


class RiskRatio(ValueObject):
    """Risk/Reward ratio computed from entry, stop and target levels.

    Use RiskRatio.from_levels() as the canonical constructor.
    """

    risk_points: float = Field(gt=0, description="Points from entry to stop")
    reward_points: float = Field(gt=0, description="Points from entry to target")

    @classmethod
    def from_levels(cls, entry: float, stop: float, target: float) -> "RiskRatio":
        risk = abs(entry - stop)
        reward = abs(target - entry)
        return cls(risk_points=risk, reward_points=reward)

    @property
    def rr(self) -> float:
        """R:R ratio rounded to 2 decimal places."""
        return round(self.reward_points / self.risk_points, 2)

    @property
    def is_acceptable(self) -> bool:
        """True if R:R meets the minimum threshold of 2:1."""
        return self.rr >= 2.0


class PriceLevel(ValueObject):
    """A named price level used in trade planning."""

    price: float = Field(gt=0)
    label: str

    @field_validator("label")
    @classmethod
    def normalize_label(cls, v: str) -> str:
        return v.lower().strip()
