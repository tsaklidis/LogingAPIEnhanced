FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/ requirements/

ARG INSTALL_DEV=false
RUN pip install --no-cache-dir -r requirements/base.txt && \
    if [ "$INSTALL_DEV" = "true" ]; then pip install --no-cache-dir -r requirements/dev.txt; fi

COPY . .

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uwsgi", "--ini", "config/uwsgi.ini"]

