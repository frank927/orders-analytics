import pytest

from app.load_data import clean_orders, parse_amount_cents


def test_cleans_orders_and_reports_rejections():
    valid_order = {
        "order_id": "1",
        "date": "2025-03-15",
        "customer": "Cliente_001",
        "country": "España",
        "product": "Teclado",
        "amount": "12.50",
        "status": "completed",
    }

    rows = [
        valid_order,
        dict(valid_order),  # Duplicado exacto.
        {
            **valid_order,
            "order_id": "2",
            "date": "16/03/2025",
            "amount": "7.25",
        },
        {
            **valid_order,
            "order_id": "3",
            "date": "2025-02-30",
        },
        {
            **valid_order,
            "order_id": "4",
            "amount": "",
        },
    ]

    cleaned, rejected, duplicate_count = clean_orders(rows)

    assert duplicate_count == 1
    assert len(cleaned) == 2
    assert len(rejected) == 2

    # Los importes se conservan exactamente en céntimos.
    by_id = {order["order_id"]: order for order in cleaned}

    assert by_id[1]["amount_cents"] == 1250
    assert by_id[2]["amount_cents"] == 725

    # La fecha recuperable se normaliza.
    assert by_id[2]["date"] == "2025-03-16"

    # Se identifican los pedidos rechazados y sus motivos.
    rejected_by_id = {
        order["order_id"]: order["reason"]
        for order in rejected
    }

    assert rejected_by_id["3"] == "Fecha inválida"
    assert rejected_by_id["4"] == "Importe vacío"

    # Todas las filas quedan contabilizadas.
    assert len(rows) == len(cleaned) + len(rejected) + duplicate_count


@pytest.mark.parametrize("amount", ["-1", "NaN", "Infinity", "1.001"])
def test_rejects_invalid_amounts(amount):
    with pytest.raises(ValueError):
        parse_amount_cents(amount)