# Northflank: servicio REST privado de Aizens NotebookLM.
# El codigo se compila desde ESTE fork (no desde PyPI).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NOTEBOOKLM_HOME=/home/app/.notebooklm

WORKDIR /src
COPY . /src

RUN python -m pip install --no-cache-dir "/src[server,android]" \
    && useradd --create-home --uid 10001 app \
    && install -m 0755 /src/northflank/start.sh /usr/local/bin/aizens-notebooklm-start

USER app
EXPOSE 10000

CMD ["/usr/local/bin/aizens-notebooklm-start"]
