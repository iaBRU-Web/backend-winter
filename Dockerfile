FROM python:3.11-slim
ENV PORT=10000
ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod -R 755 /app/api/info && \
    chmod 644 /app/api/brain.txt

EXPOSE 10000

CMD uvicorn api.index:app --host 0.0.0.0 --port ${PORT}
