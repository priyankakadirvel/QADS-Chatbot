FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

ENV PYTHONPATH=/app/backend:$PYTHONPATH

CMD ["gunicorn", "-c", "gunicorn.conf.py", "backend.main:app"]
