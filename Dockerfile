FROM frolvlad/alpine-glibc:latest

LABEL maintainer="tgabriel@redhat.com"
LABEL description="Lightweight curator"

ARG OC_VERSION=4.5
ARG BUILD_DEPS='gzip curl tar'
ARG RUN_DEPS='ca-certificates gettext bash python3'

USER root

RUN python3 -m ensurepip && \
    rm -r /usr/lib/python*/ensurepip && \
    pip3 install --upgrade pip setuptools && \
    if [ ! -e /usr/bin/pip ]; then ln -s pip3 /usr/bin/pip ; fi && \
    if [[ ! -e /usr/bin/python ]]; then ln -sf /usr/bin/python3 /usr/bin/python; fi && \
    pip install elasticsearch && \
    apk --no-cache add $BUILD_DEPS $RUN_DEPS && \
    curl -sLo /tmp/oc.tar.gz https://mirror.openshift.com/pub/openshift-v$(echo $OC_VERSION | cut -d'.' -f 1)/clients/oc/$OC_VERSION/linux/oc.tar.gz && \
    tar xzvf /tmp/oc.tar.gz -C /usr/local/bin/ && \
    rm -rf /tmp/oc.tar.gz && \
    apk del $BUILD_DEPS && \
    rm -r /root/.cache && \
    chown -R nobody:nobody /home

USER nobody

COPY ./scripts/curator.py /home/

ENTRYPOINT ["tail", "-f", "/dev/null"]
