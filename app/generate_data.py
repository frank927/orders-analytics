import csv
import random
from datetime import date, timedelta
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = PROJECT_ROOT / "data" / "orders_raw.csv"

SEED = 42
ORDER_COUNT = 1_200
DUPLICATE_COUNT = 30

FIELDNAMES = [
    "order_id",
    "date",
    "customer",
    "country",
    "product",
    "amount",
    "status",
]


def generate_orders() -> list[dict[str, str | int]]:
    rng = random.Random(SEED)
    start_date = date(2025, 1, 1)

    countries = ["España", "México", "Argentina", "Colombia", "Chile"]
    products = ["Teclado", "Ratón", "Monitor", "Auriculares", "Webcam"]
    statuses = ["completed", "pending", "cancelled"]

    orders = []

    for order_id in range(1, ORDER_COUNT + 1):
        order_date = start_date + timedelta(days=rng.randrange(365))
        amount_cents = rng.randint(500, 50_000)

        orders.append(
            {
                "order_id": order_id,
                "date": order_date.isoformat(),
                "customer": f"Cliente_{rng.randint(1, 100):03d}",
                "country": rng.choice(countries),
                "product": rng.choice(products),
                "amount": (
                    f"{amount_cents // 100}.{amount_cents % 100:02d}"
                ),
                "status": rng.choice(statuses),
            }
        )

    # Grupos separados para poder verificar los errores introducidos.
    error_indices = rng.sample(range(ORDER_COUNT), 60)

    for index in error_indices[:20]:
        orders[index]["date"] = "2025-02-30"

    for index in error_indices[20:40]:
        orders[index]["amount"] = ""

    for index in error_indices[40:60]:
        original_date = date.fromisoformat(str(orders[index]["date"]))
        orders[index]["date"] = original_date.strftime("%d/%m/%Y")

    # Copias independientes de pedidos ya existentes.
    duplicates = [
        order.copy()
        for order in rng.sample(orders, DUPLICATE_COUNT)
    ]
    orders.extend(duplicates)
    rng.shuffle(orders)

    return orders


def main() -> None:
    orders = generate_orders()
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)

    with CSV_PATH.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(orders)

    print(f"CSV generado: {CSV_PATH}")
    print(f"Filas: {len(orders)}")
    print(f"Pedidos originales: {ORDER_COUNT}")
    print(f"Duplicados añadidos: {DUPLICATE_COUNT}")


if __name__ == "__main__":
    main()