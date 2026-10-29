# REST server de notebooklm-py, compilado desde ESTE fork.
# No se necesita Chromium/Playwright: backend Android con master token.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NOTEBOOKLM_HOME=/home/app/.notebooklm

WORKDIR /src
COPY . /src
RUN python -m pip install --no-cache-dir "/src[server,android]" \
    && useradd --create-home --uid 10001 app \
    && install -m 0755 /src/render/start.sh /opt/notebooklm-start

USER app
EXPOSE 10000
CMD ["/opt/notebooklm-start"]
