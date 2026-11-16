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