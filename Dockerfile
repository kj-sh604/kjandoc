FROM ubuntu:24.04

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# system deps + libreoffice fresh ppa
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        software-properties-common \
        ca-certificates && \
    add-apt-repository -y ppa:libreoffice/ppa && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-venv \
        libreoffice \
        poppler-utils \
        fonts-liberation \
        fonts-dejavu-core && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# python deps
COPY src/requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir --no-compile --break-system-packages -r /tmp/requirements.txt

# kjandoc binary -> /usr/local/bin
COPY src/kjandoc /usr/local/bin/kjandoc
RUN chmod +x /usr/local/bin/kjandoc

# demoware
WORKDIR /app
COPY demoware/ /app/

# storage dirs
RUN mkdir -p /app/uploads /app/output

EXPOSE 8080

CMD ["python3", "server.py"]