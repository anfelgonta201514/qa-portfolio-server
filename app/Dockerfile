FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# UN solo proceso con varios hilos (QAP-18):
# - Hilos: la llamada al proveedor de IA puede tardar hasta 15 s; con un worker síncrono bloquearía el sitio entero.
# - Un solo proceso (--workers=1): los límites de la IA y del login viven en memoria; con más procesos cada uno
#   tendría su propio contador y los límites dejarían de valer (hay pruebas que vigilan esto).
# - --timeout: el worker muere si una petición tarda más; debe superar con margen el timeout del proveedor (15 s).
CMD ["gunicorn", "--bind=0.0.0.0:8000", "--workers=1", "--worker-class=gthread", "--threads=4", "--timeout=30", "app:app"]
