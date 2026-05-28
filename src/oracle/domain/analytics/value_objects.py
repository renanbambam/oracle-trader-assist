"""Analytics domain — value objects."""

from pydantic import Field

from oracle.domain.shared.base import ValueObject


class WinRate(ValueObject):
    """Win/loss/breakeven counts with derived percentage."""

    wins: int = Field(ge=0)
    losses: int = Field(ge=0)
    breakevens: int = Field(default=0, ge=0)

    @property
    def total(self) -> int:
        return self.wins + self.losses + self.breakevens

    @property
    def pct(self) -> float:
        if self.total == 0:
            return 0.0
        return round(self.wins / self.total * 100, 1)

    @property
    def is_profitable(self) -> bool:
        return self.pct > 50.0


class ExpectedValue(ValueObject):
    """Statistical expectancy per trade, expressed in R multiples.

    Positive EV means the strategy is mathematically profitable over time.
    EV = win_prob * avg_win_R - loss_prob * avg_loss_R
    """

    average_win_r: float = Field(ge=0)
    average_loss_r: float = Field(ge=0)
    win_rate_pct: float = Field(ge=0, le=100)

    @property
    def ev_r(self) -> float:
        win_prob = self.win_rate_pct / 100
        loss_prob = 1 - win_prob
        return round(win_prob * self.average_win_r - loss_prob * self.average_loss_r, 3)

    @property
    def is_positive(self) -> bool:
        return self.ev_r > 0


class DrawdownMetric(ValueObject):
    """Drawdown statistics expressed in R multiples."""

    max_drawdown_r: float = Field(ge=0, description="Largest historical drawdown in R")
    current_drawdown_r: float = Field(ge=0, description="Current open drawdown in R")
    max_consecutive_losses: int = Field(ge=0)
    current_consecutive_losses: int = Field(ge=0)

    @property
    def is_in_drawdown(self) -> bool:
        return self.current_drawdown_r > 0

    @property
    def is_critical(self) -> bool:
        """True if current drawdown exceeds daily risk limit equivalent (3R)."""
        return self.current_drawdown_r >= 3.0
