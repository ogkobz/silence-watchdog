FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY watchdog ./watchdog
COPY config.example.yaml ./config.yaml

# Данные — на томе: перезапуск контейнера не должен обнулять историю событий,
# иначе после каждого деплоя сторож считает, что все источники молчат с нуля.
VOLUME ["/app/data"]
ENV WATCHDOG_DB=/app/data/watchdog.db

EXPOSE 8080
CMD ["uvicorn", "watchdog.app:app", "--host", "0.0.0.0", "--port", "8080"]
