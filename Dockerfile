FROM python:3.14-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# ---------------------------------------------------------
# SYSTEM DEPENDENCIES
# ---------------------------------------------------------

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libreoffice-writer \
        libreoffice-impress \
        libreoffice-common \
        fonts-dejavu \
        fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------
# PYTHON DEPENDENCIES
# ---------------------------------------------------------

COPY requirements.txt .

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt

# ---------------------------------------------------------
# APPLICATION
# ---------------------------------------------------------

COPY . .

# ---------------------------------------------------------
# STATIC FILES
# ---------------------------------------------------------

RUN python manage.py collectstatic --noinput

# ---------------------------------------------------------
# PORT
# ---------------------------------------------------------

EXPOSE 10000

# ---------------------------------------------------------
# START SCORE SKILL
# ---------------------------------------------------------

CMD ["sh", "-c", "uvicorn config.asgi:application --host 0.0.0.0 --port ${PORT:-10000}"]