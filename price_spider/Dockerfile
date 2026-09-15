FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Устанавливаем xvfb для имитации реального монитора
RUN apt-get update && apt-get install -y xvfb && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install -U "camoufox[geoip]"
# RUN pip install -U "camoufox"
RUN python3 -m camoufox fetch

# Установка системных зависимостей только для Chromium (экономит место)
RUN playwright install chromium

COPY . .
RUN rm -rf venv html_dumps screenshots logs/*

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]

# Запускаем uvicorn ЧЕРЕЗ xvfb-run с эмуляцией экрана 1920x1080 и 24-битным цветом
#CMD ["xvfb-run", "--server-args=-screen 0 1920x1080x24", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
