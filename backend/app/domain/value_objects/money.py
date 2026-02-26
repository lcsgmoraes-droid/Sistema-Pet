from decimal import Decimal, ROUND_HALF_UP


class Money:
    """
    Value Object monetário (DDD SAFE).
    Imutável.
    """

    def __init__(self, value):
        self._value = Decimal(str(value)).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        if self._value < 0:
            raise ValueError("Money não pode ser negativo")

    @property
    def value(self):
        return float(self._value)

    def __add__(self, other):
        return Money(self._value + Decimal(str(other.value)))

    def __mul__(self, qty):
        return Money(self._value * Decimal(str(qty)))

    def __repr__(self):
        return f"Money({self.value})"
