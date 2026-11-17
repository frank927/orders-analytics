# Orders Analytics

Proyecto de análisis de pedidos con Python, SQLite, FastAPI y un LLM
local mediante Ollama.

Permite generar datos con errores controlados, limpiarlos, consultar
vistas SQL y formular preguntas en lenguaje natural. El SQL generado
por el modelo se valida antes de ejecutarse sobre una conexión
de solo lectura.

## Estado de verificación

- Generación y carga comprobadas: 1.160 pedidos válidos.
- Vistas SQL comprobadas contra los datos de origen.
- Última ejecución de la suite: 40 casos aprobados.
- Integración con Ollama implementada y probada con HTTP simulado.
- Pendiente: comprobar el recorrido completo con el modelo local real.

## Requisitos

- Python 3.14.0, versión utilizada durante el desarrollo.
- Dependencias de Python registradas en requirements.txt.
- Ollama para ejecutar preguntas con un modelo real.
- Modelo qwen2.5-coder:1.5b descargado en Ollama.

Los tests no necesitan Ollama, un modelo descargado ni credenciales.

## Instalación y ejecución en Windows PowerShell

Ejecuta los comandos desde la raíz del repositorio.

### 1. Crear el entorno e instalar dependencias

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
```

No es necesario activar el entorno: los comandos utilizan directamente
su ejecutable de Python.

### 2. Preparar Ollama

Instala Ollama desde:

https://ollama.com/download/windows

Abre una nueva terminal después de instalarlo y ejecuta:

```powershell
ollama --version
ollama pull qwen2.5-coder:1.5b
```

Ollama se instala por separado del entorno virtual de Python.
Debe permanecer iniciado para atender las preguntas de la aplicación.

### 3. Configurar la aplicación

```powershell
Copy-Item .env.example .env
```

Contenido de la configuración:

```dotenv
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5-coder:1.5b
```

La integración local no requiere una clave de OpenAI ni saldo
en un proveedor externo. El archivo .env está excluido de Git.

### 4. Generar, limpiar y cargar los pedidos

```powershell
.\.venv\Scripts\python.exe -m app.generate_data
.\.venv\Scripts\python.exe -m app.load_data
.\.venv\Scripts\python.exe -m app.create_views
```

Archivos utilizados o generados:

| Archivo | Contenido |
|---|---|
| data/orders_raw.csv | Pedidos originales con errores controlados |
| data/orders.db | Base SQLite con los pedidos válidos y las vistas |
| data/orders_rejected.csv | Filas rechazadas y sus motivos |

La base de datos y el archivo de rechazos se generan localmente
y están excluidos de Git.

### 5. Arrancar FastAPI

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

- Comprobación: http://127.0.0.1:8000/health
- Documentación interactiva: http://127.0.0.1:8000/docs

Desde /docs se puede probar POST /ask mediante la opción
"Try it out".

## Ejemplo de petición

POST /ask recibe:

```json
{
  "question": "¿Cuánto vendimos en España en marzo de 2025?"
}
```

También puede enviarse desde otra terminal PowerShell:

```powershell
$questionBody = @{
    question = "¿Cuánto vendimos en España en marzo de 2025?"
} | ConvertTo-Json

Invoke-RestMethod `
    -Method Post `
    -Uri "http://127.0.0.1:8000/ask" `
    -ContentType "application/json; charset=utf-8" `
    -Body ([System.Text.Encoding]::UTF8.GetBytes($questionBody)) |
    ConvertTo-Json -Depth 10
```

La respuesta contiene:

| Campo | Significado |
|---|---|
| question | Pregunta recibida |
| sql | Consulta validada y ejecutada |
| rows | Filas devueltas |
| row_count | Número de filas incluidas en la respuesta |
| truncated | Indica si quedaron filas fuera del límite de resultados |

Como referencia para verificar el modelo, la consulta SQL directa
sobre España en marzo de 2025 devuelve 9 pedidos completados y
2.222,34 EUR. Este resultado se comprobó en SQLite; todavía está
pendiente contrastarlo mediante el endpoint con el LLM real.

## Datos y reglas de limpieza

El generador utiliza la semilla 42 y produce 1.200 pedidos originales
del año 2025 más 30 copias exactas.

Entre los pedidos originales se introducen tres grupos separados:

- 20 fechas imposibles.
- 20 importes vacíos.
- 20 fechas en formato DD/MM/YYYY, recuperables durante la limpieza.

Todos los importes representan EUR, independientemente del país.
Los clientes son ficticios y se representan con códigos como
Cliente_001. Un cliente puede tener varios pedidos.

Reglas aplicadas:

- Eliminar filas duplicadas exactas.
- Aceptar fechas YYYY-MM-DD y DD/MM/YYYY y normalizarlas a YYYY-MM-DD.
- Rechazar fechas imposibles e importes vacíos o inválidos.
- Exigir importes positivos con precisión máxima de céntimos.
- Rechazar campos obligatorios vacíos y estados desconocidos.
- Detener la carga si dos pedidos válidos distintos comparten ID.

El campo order_id identifica el pedido. La eliminación de duplicados
exige coincidencia de todos los campos originales; no se eliminan
pedidos legítimos solo por compartir cliente, fecha o importe.

Los importes se almacenan como céntimos enteros para evitar errores
de precisión de coma flotante en los datos almacenados.

Resultado comprobado:

| Concepto | Filas |
|---|---:|
| Entrada | 1.230 |
| Duplicados eliminados | 30 |
| Rechazadas | 40 |
| Guardadas en SQLite | 1.160 |

La carga reemplaza el contenido de orders dentro de una transacción.
Repetirla con el mismo CSV mantiene el mismo resultado.

## Vistas SQL y criterios de negocio

Las definiciones se encuentran en app/views.sql.

| Vista | Contenido |
|---|---|
| monthly_sales | Ventas por año-mes y país |
| top_customers | Los diez clientes con mayor importe total comprado |

Solo los pedidos con estado completed cuentan como ventas.
Los estados pending y cancelled se conservan en orders, pero quedan
fuera de ambas vistas.

Los totales se calculan en céntimos enteros. Las vistas incluyen
también una columna expresada en EUR para facilitar su lectura.

Los empates del ranking se resuelven por identificador de cliente.
top_customers contiene el ranking global de diez clientes, no un
ranking recalculado por país o periodo.

Las preguntas sin año se interpretan sobre 2025, el año de los datos.
Esta regla se comunica al LLM en el prompt.

## Flujo de una pregunta

1. FastAPI valida el cuerpo de la petición.
2. El proveedor envía a Ollama la pregunta y el esquema de datos.
3. El modelo devuelve un JSON con SQL o un motivo de rechazo.
4. Pydantic valida la estructura de esa respuesta.
5. SQLGlot comprueba la consulta SQL.
6. El ejecutor abre SQLite en modo de solo lectura y consulta los datos.
7. FastAPI devuelve el resultado o un error controlado.

El modelo recibe la descripción de las tablas y la pregunta;
no se le envían las filas del CSV.

## Validación y límites de ejecución

La política admite una sola sentencia SELECT sobre una sola fuente:

- orders
- monthly_sales
- top_customers

Se utiliza una lista explícita de estructuras y funciones permitidas.
Esta versión rechaza subconsultas, CTE, JOIN, UNION, referencias
a otras bases de datos y acceso al catálogo interno.

El ejecutor utiliza además:

- Conexión SQLite de solo lectura.
- Autorizador de operaciones, fuentes y funciones.
- Máximo de 100 filas por respuesta.
- Supervisión periódica de la ejecución SQL con un umbral de
  dos segundos.
- Cierre de la conexión al finalizar o producirse un error.

El límite temporal de SQL se comprueba cada 1.000 instrucciones
internas de SQLite; no es un corte exacto de tiempo real.
Es independiente de la espera de la respuesta del LLM.

La llamada a Ollama utiliza un tiempo de espera de lectura de
120 segundos y de conexión de 5 segundos. No hay reintentos
automáticos.

Una respuesta JSON bien formada no garantiza que el SQL sea seguro:
la validación SQL se ejecuta igualmente. Tampoco garantiza que el
modelo haya interpretado correctamente la pregunta.

## Errores de la API

La pregunta debe contener entre 1 y 1.000 caracteres, después
de eliminar espacios al principio y al final.

| Código HTTP | Situación |
|---|---|
| 422 | Entrada inválida, SQL no permitido o consulta no ejecutable |
| 502 | Fallo de conexión con Ollama, tiempo de espera agotado o respuesta inválida del modelo |

Los errores controlados se devuelven en el campo detail.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

La suite incluye pruebas de:

- Limpieza, normalización, duplicados y rechazos.
- Validación de importes.
- Aceptación y rechazo de consultas SQL.
- Ejecución de COUNT(*) con el autorizador activado.
- Endpoint con LLM simulado y SQLite temporal.
- Conservación de los datos ante una consulta de escritura rechazada.
- Errores del proveedor y respuestas mal formadas.
- Tiempo de espera del proveedor.
- Validación de las preguntas recibidas.

El proveedor se sustituye mediante dependency_overrides de FastAPI
en los tests del endpoint. Las pruebas de la integración con Ollama
simulan la comunicación HTTP.

Las bases de prueba son temporales y no modifican data/orders.db.

## Organización del código

| Archivo | Responsabilidad |
|---|---|
| app/generate_data.py | Generar el CSV reproducible |
| app/load_data.py | Limpiar los pedidos y cargarlos en SQLite |
| app/views.sql | Definir las dos vistas SQL |
| app/create_views.py | Crear las vistas en la base de datos |
| app/sql_validation.py | Validar el SQL mediante SQLGlot |
| app/query_executor.py | Ejecutar consultas con permisos y límites |
| app/llm.py | Comunicarse con Ollama y validar su respuesta JSON |
| app/main.py | Exponer los endpoints de FastAPI |
| tests/ | Pruebas automatizadas |

## Decisiones técnicas

- SQLite facilita la ejecución sin configurar un servidor de datos.
- La limpieza está separada de la persistencia para poder probar
  sus reglas sin acceder a archivos ni a la base de datos.
- Los importes vacíos se rechazan en lugar de sustituirse por cero,
  porque esa sustitución alteraría las ventas.
- Las vistas centralizan los criterios de agregación.
- FastAPI aporta validación de entrada y documentación interactiva.
- La generación de SQL está separada del endpoint para sustituir
  el proveedor durante las pruebas.
- Ollama permite ejecutar un modelo real sin depender de la
  facturación de un proveedor externo.
- Se eligió inicialmente un modelo de 1.5B por las limitaciones
  del equipo de desarrollo, con 8 GB de RAM.
- La política SQL limitada reduce el alcance de consultas admitidas
  y facilita revisar su comportamiento.

## Limitaciones y mejoras con más tiempo

- Evaluar la exactitud del modelo con un conjunto de preguntas y
  resultados esperados, incluyendo ambigüedades y solicitudes
  que no se pueden responder.
- Medir latencia y consumo de memoria del modelo local y comparar
  alternativas según el hardware disponible.
- Ampliar la cobertura de tests de permisos, vistas, límites
  y fallos de ejecución.
- Incorporar validación de columnas y ampliar las construcciones
  SQL admitidas únicamente si lo requieren los casos de uso.
- Añadir logging estructurado y métricas sin registrar secretos.
- Incorporar autenticación y límites de peticiones antes de exponer
  la aplicación fuera del entorno local.
- Automatizar los tests en GitHub Actions.

## Uso de IA

Se utilizó ChatGPT como apoyo durante el desarrollo.

### Qué se le pidió

- Proponer una estructura ajustada al enunciado.
- Explicar FastAPI y su mecanismo de dependencias.
- Proponer el generador reproducible y las reglas de limpieza.
- Ayudar a implementar las vistas, la validación SQL y el ejecutor.
- Proponer tests y la integración con un modelo local.
- Revisar las instrucciones de ejecución y la documentación.

### Qué se aceptó

Se incorporaron las propuestas de estructura y código, revisando
su funcionamiento mediante ejecución manual y tests.

Se aceptaron SQLite, los importes en céntimos enteros, la separación
entre proveedor y endpoint, y el uso de dependencias sustituibles
para probar la API sin llamar al modelo real.

### Qué se corrigió o ajustó

- Se detectó una instalación externa de PySpark accesible mediante
  PYTHONPATH. Se eliminó esa variable de la sesión de PowerShell
  antes de registrar las dependencias.
- Una comprobación manual sobre España devolvía un resultado vacío
  porque PowerShell alteraba la ñ al enviar código por una tubería.
  Se verificó la consulta utilizando un escape Unicode.
- Se corrigió una condición del autorizador propuesto: COUNT(*)
  podía generar una lectura con database_name=None y columna vacía.
  Se inspeccionaron los argumentos reales y se añadió un test
  de regresión con una base temporal.
- Se descartó la integración inicial prevista con OpenAI y se adaptó
  el proveedor a Ollama local por las restricciones de pago.
- Se actualizaron las instrucciones para distinguir los tests
  simulados de la comprobación pendiente con un modelo real.

La última ejecución comunicada incluye 40 casos aprobados.
La inferencia real con Ollama todavía está pendiente de comprobar.

## Incidencia del entorno de desarrollo

Si pip detecta paquetes externos al entorno virtual, comprueba
la variable PYTHONPATH.

Durante el desarrollo se eliminó únicamente de la sesión actual:

```powershell
Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
```

Esta medida resolvió la interferencia con una instalación externa
de Spark sin modificar la configuración permanente del equipo.