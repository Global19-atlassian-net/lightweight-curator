FROM frolvlad/alpine-glibc:latest

LABEL maintainer="tgabriel@redhat.com"
LABEL description="Lightweight curator image"

ARG OC_VERSION=4.5
ARG BUILD_DEPS='tar gzip curl'
ARG RUN_DEPS='curl ca-certificates gettext'

RUN apk add --no-cache python3 && \
    apk add --no-cache curl && \
    apk add --no-cache tar && \
    apk add --no-cache bash && \
    python3 -m ensurepip && \
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
    rm -r /root/.cache

ADD ./curator.py ./es-used-disk ./env-prep  /home/

#ENTRYPOINT ["python", "/home/curator.py"]
ENTRYPOINT ["tail", "-f", "/dev/null"]
