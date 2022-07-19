FROM python:3.10-slim-bullseye

WORKDIR /app

ADD . .

RUN set -eux && \
    apt update && \
    apt install -y gcc && \
    pip install -U pip setuptools && \
    pip install -r requirements.txt && \
    install-nplinker-deps

# set a HOME variable because things often break if it's left unset
ENV HOME "/data"
# tell the webapp to look for a config called nplinker.toml in /data,
# which should be an external volume
ENV NPLINKER_CONFIG "/data/nplinker.toml"
# unbuffered console output, since the user guide tells people to watch
# for certain messages which may not appear as expected if they get buffered
ENV PYTHONUNBUFFERED "1"

# default bokeh server port
EXPOSE 5006/tcp

CMD ["bokeh", "serve", "nplinker"]
