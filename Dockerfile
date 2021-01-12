FROM frolvlad/alpine-glibc:latest

LABEL maintainer="tgabriel@redhat.com"
LABEL description="Lightweight Curator"

ARG OC_VERSION=4.5
ARG BUILD_DEPS='gzip curl tar'
ARG RUN_DEPS='ca-certificates gettext bash python3'

USER root

RUN apk --no-cache add $BUILD_DEPS $RUN_DEPS && \
    python3 -m ensurepip && \
    rm -r /usr/lib/python*/ensurepip && \
    pip3 install --upgrade pip setuptools elasticsearch pytest && \
    if [ ! -e /usr/bin/pip ]; then ln -s pip3 /usr/bin/pip ; fi && \
    if [[ ! -e /usr/bin/python ]]; then ln -sf /usr/bin/python3 /usr/bin/python; fi && \
    apk del $BUILD_DEPS && \
    export PYTHONPATH=/home/ && \
    chmod +x /home/lightweight_curator.py /home/lightweight_curator_test.py && \
    rm -r /root/.cache && \
    chown -R nobody:nobody /home

USER nobody

COPY ./scripts/ /home/

ENTRYPOINT ["tail", "-f", "/dev/null"]
