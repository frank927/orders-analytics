# Orders Analytics

Proyecto de análisis de pedidos con Python, SQLite, FastAPI y un LLM.

## Estado actual

Entorno configurado y endpoint GET /health verificado.
Pendientes: generación y limpieza de datos, vistas SQL, consultas con LLM y tests.

## Requisitos

- Python 3.14, versión utilizada durante el desarrollo.
- Dependencias registradas en requirements.txt.

## Ejecutar en Windows PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

- Comprobación: http://127.0.0.1:8000/health
- Documentación interactiva: http://127.0.0.1:8000/docs

## Decisiones

- SQLite para facilitar la ejecución sin servicios externos.
- FastAPI para exponer la API y su documentación interactiva.
- Versiones instaladas registradas en requirements.txt.

## Uso de IA

Se utilizó ChatGPT como apoyo para planificar el proyecto y proponer
la configuración inicial.

Se aceptó la estructura inicial y se verificaron manualmente
los endpoints /health y /docs.

Durante la configuración, pip detectó una instalación externa de
PySpark mediante PYTHONPATH. Con ayuda de la IA se diagnosticó el
problema y se eliminó esa variable únicamente de la sesión de
PowerShell antes de registrar las dependencias.

Se pidió a ChatGPT una propuesta de generador reproducible con errores
controlados. Se incorporó el código y se comprobó el número de filas,
los identificadores distintos y las copias adicionales.

## Generación de datos

```powershell
.\.venv\Scripts\python.exe -m app.generate_data
```

El generador utiliza la semilla 42 y produce 1.200 pedidos originales
de 2025 más 30 duplicados exactos.

Entre los pedidos originales se introducen tres grupos separados:
20 fechas imposibles, 20 importes vacíos y 20 fechas en formato
DD/MM/YYYY que se normalizarán durante la limpieza.

Todos los importes representan EUR, independientemente del país.
Los clientes son ficticios y se representan con códigos como Cliente_001.
Un mismo cliente puede tener varios pedidos.

El campo order_id permite identificar los duplicados sin eliminar
pedidos legítimos que compartan otros valores.

## Limpieza y carga

Primero genera el CSV y después ejecuta:

```powershell
.\.venv\Scripts\python.exe -m app.load_data
```

El proceso guarda los pedidos válidos en data/orders.db y las filas
rechazadas con su motivo en data/orders_rejected.csv.

Reglas de limpieza:

- Se eliminan las filas duplicadas exactas.
- Se aceptan fechas YYYY-MM-DD y DD/MM/YYYY y se guardan en formato ISO.
- Se rechazan fechas imposibles e importes vacíos o inválidos.
- Los importes deben ser positivos y tener precisión máxima de céntimos.
- Se rechazan campos obligatorios vacíos y estados desconocidos.
- Si dos pedidos válidos distintos comparten ID, se detiene la carga
  para revisar el conflicto.

Los importes se almacenan como céntimos enteros para evitar errores
de precisión de coma flotante.

La carga reemplaza el contenido de la tabla en una transacción.
Repetirla con el mismo CSV mantiene el mismo resultado.

Resultado comprobado con los datos generados:
1.230 filas de entrada, 30 duplicados eliminados,
40 filas rechazadas y 1.160 pedidos guardados.

## Vistas SQL

Después de cargar los pedidos:

```powershell
.\.venv\Scripts\python.exe -m app.create_views
```

Las definiciones se encuentran en app/views.sql.

- monthly_sales: ventas por año-mes y país.
- top_customers: los 10 clientes con mayor importe total comprado.

Ambas vistas incluyen únicamente pedidos con estado completed.
Los pendientes y cancelados se conservan en orders, pero no cuentan
como ventas.

Los totales se calculan en céntimos enteros. También se ofrece una
columna expresada en EUR para facilitar su lectura.

Los empates del ranking se resuelven ordenando por identificador
de cliente.

## Validación SQL

La consulta generada por el LLM se analiza con SQLGlot usando
el dialecto SQLite.

Solo se admite una sentencia SELECT sobre una de estas fuentes:
orders, monthly_sales o top_customers.

Se utiliza una lista explícita de estructuras y funciones permitidas.
Esta versión no admite subconsultas, CTE, JOIN ni UNION.
Tampoco permite consultar el catálogo interno ni otras bases de datos.

La validación no garantiza que la consulta responda correctamente
a la intención del usuario. Los errores de columnas o de ejecución
se gestionarán en la API.

## Ejecutar los tests

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```