import csv
import json
import sqlite3
from datetime import datetime
from decimal import Decimal, InvalidOperation

from app.generate_data import CSV_PATH, FIELDNAMES, PROJECT_ROOT


DB_PATH = PROJECT_ROOT / "data" / "orders.db"
REJECTED_PATH = PROJECT_ROOT / "data" / "orders_rejected.csv"

VALID_STATUSES = {"completed", "pending", "cancelled"}


def normalize_date(value: str) -> str:
    for date_format in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, date_format).date().isoformat()
        except ValueError:
            continue

    raise ValueError("Fecha inválida")


def parse_amount_cents(value: str) -> int:
    if not value:
        raise ValueError("Importe vacío")

    try:
        amount = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("Importe no numérico") from exc

    if not amount.is_finite() or amount <= 0:
        raise ValueError("El importe debe ser finito y positivo")

    cents = amount * 100

    if cents != cents.to_integral_value():
        raise ValueError("El importe tiene más de dos decimales")

    # Límite del entero de 64 bits utilizado por SQLite.
    if cents > 9_223_372_036_854_775_807:
        raise ValueError("Importe fuera del rango admitido")

    return int(cents)


def clean_orders(
    rows: list[dict[str, str]],
) -> tuple[list[dict], list[dict], int]:
    cleaned = []
    rejected = []
    seen_rows = set()
    accepted_ids = set()
    duplicate_count = 0

    for row in rows:
        # La firma incluye todos los campos del CSV original.
        signature = tuple(row[field] for field in FIELDNAMES)

        if signature in seen_rows:
            duplicate_count += 1
            continue

        seen_rows.add(signature)

        try:
            values = {
                field: (row[field] or "").strip()
                for field in FIELDNAMES
            }

            order_id = int(values["order_id"])
            if order_id <= 0:
                raise ValueError("El identificador debe ser positivo")

            order_date = normalize_date(values["date"])
            amount_cents = parse_amount_cents(values["amount"])

            for field in ("customer", "country", "product"):
                if not values[field]:
                    raise ValueError(f"Campo obligatorio vacío: {field}")

            if values["status"] not in VALID_STATUSES:
                raise ValueError("Estado no permitido")

        except ValueError as exc:
            rejected.append({**row, "reason": str(exc)})
            continue

        # Dos filas distintas con el mismo ID requieren revisión.
        # No elegimos una de ellas arbitrariamente.
        if order_id in accepted_ids:
            raise ValueError(
                f"Hay pedidos válidos distintos con el mismo ID: {order_id}"
            )

        accepted_ids.add(order_id)
        cleaned.append(
            {
                "order_id": order_id,
                "date": order_date,
                "customer": values["customer"],
                "country": values["country"],
                "product": values["product"],
                "amount_cents": amount_cents,
                "status": values["status"],
            }
        )

    return cleaned, rejected, duplicate_count


def save_orders(orders: list[dict]) -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                order_id INTEGER PRIMARY KEY CHECK (order_id > 0),
                date TEXT NOT NULL,
                customer TEXT NOT NULL,
                country TEXT NOT NULL,
                product TEXT NOT NULL,
                amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
                status TEXT NOT NULL
                    CHECK (status IN ('completed', 'pending', 'cancelled'))
            )
            """
        )

        # El reemplazo completo se confirma solo si la carga termina bien.
        connection.execute("DELETE FROM orders")
        connection.executemany(
            """
            INSERT INTO orders (
                order_id, date, customer, country,
                product, amount_cents, status
            )
            VALUES (
                :order_id, :date, :customer, :country,
                :product, :amount_cents, :status
            )
            """,
            orders,
        )


def main() -> None:
    with CSV_PATH.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)

        if reader.fieldnames != FIELDNAMES:
            raise ValueError("Las columnas del CSV no coinciden con las esperadas")

        rows = list(reader)

    cleaned, rejected, duplicate_count = clean_orders(rows)
    save_orders(cleaned)

    with REJECTED_PATH.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=[*FIELDNAMES, "reason"])
        writer.writeheader()
        writer.writerows(rejected)

    print(
        json.dumps(
            {
                "input_rows": len(rows),
                "duplicates_removed": duplicate_count,
                "rejected_rows": len(rejected),
                "loaded_rows": len(cleaned),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()