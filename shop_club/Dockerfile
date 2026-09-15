FROM python:3.11-slim-bookworm

WORKDIR /app

# Оптимизация pip-кэша
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Удаляем ненужные локальные папки, если они случайно попали в контекст
RUN rm -rf venv

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
