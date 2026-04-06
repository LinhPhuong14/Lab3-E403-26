import json


def estimate_travel_budget(
    days: int, people: int, base_fare: float
) -> str:
    """
    Budget formula: days * people * base_fare
    """
    if days <= 0:
        raise ValueError("days must be > 0")
    if people <= 0:
        raise ValueError("people must be > 0")
    if base_fare < 0:
        raise ValueError("base_fare must be >= 0")

    total_budget = round(days * people * base_fare, 2)
    return json.dumps(
        {
            "days": days,
            "people": people,
            "base_fare": base_fare,
            "total_budget": total_budget,
            "currency": "USD",
        },
        ensure_ascii=False,
    )
