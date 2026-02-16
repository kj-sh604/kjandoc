FROM ubuntu:24.04

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

ARG DEBIAN_FRONTEND=noninteractive

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
        fonts-liberation2 \
        fonts-dejavu \
        fonts-dejavu-extra \
        fonts-noto \
        fonts-noto-color-emoji \
        fonts-noto-core \
        fonts-noto-extra \
        fonts-noto-ui-core \
        fonts-noto-ui-extra \
        fonts-noto-cjk \
        fonts-noto-cjk-extra \
        fonts-noto-hinted \
        fonts-noto-unhinted \
        fonts-freefont-ttf \
        fonts-urw-base35 \
        fonts-font-awesome \
        fonts-powerline \
        ttf-mscorefonts-installer \
        fonts-cascadia-code \
        fonts-firacode \
        fonts-roboto \
        fonts-roboto-slab \
        fonts-ubuntu \
        fonts-hack \
        fonts-lato \
        fonts-open-sans \
        fonts-inconsolata \
        fonts-droid-fallback \
        fonts-symbola \
        fonts-ancient-scripts \
        fonts-indic \
        fonts-beng \
        fonts-deva \
        fonts-gargi \
        fonts-gubbi \
        fonts-gujr \
        fonts-guru \
        fonts-kalapi \
        fonts-knda \
        fonts-lohit-beng-assamese \
        fonts-lohit-beng-bengali \
        fonts-lohit-deva \
        fonts-lohit-gujr \
        fonts-lohit-guru \
        fonts-lohit-knda \
        fonts-lohit-mlym \
        fonts-lohit-orya \
        fonts-lohit-taml \
        fonts-lohit-taml-classical \
        fonts-lohit-telu \
        fonts-mlym \
        fonts-navilu \
        fonts-orya \
        fonts-pagul \
        fonts-sahadeva \
        fonts-samyak-deva \
        fonts-samyak-gujr \
        fonts-samyak-mlym \
        fonts-samyak-taml \
        fonts-sarai \
        fonts-smc \
        fonts-taml \
        fonts-telu \
        fonts-tlwg-garuda \
        fonts-tlwg-kinnari \
        fonts-tlwg-loma \
        fonts-tlwg-mono \
        fonts-tlwg-norasi \
        fonts-tlwg-purisa \
        fonts-tlwg-sawasdee \
        fonts-tlwg-typewriter \
        fonts-tlwg-typist \
        fonts-tlwg-typo \
        fonts-tlwg-umpush \
        fonts-tlwg-waree \
        fonts-arphic-ukai \
        fonts-arphic-uming \
        fonts-wqy-microhei \
        fonts-wqy-zenhei \
        fonts-ipafont \
        fonts-ipafont-gothic \
        fonts-ipafont-mincho \
        fonts-ipaexfont \
        fonts-ipaexfont-gothic \
        fonts-ipaexfont-mincho \
        fonts-takao \
        fonts-takao-gothic \
        fonts-takao-mincho \
        fonts-vlgothic \
        fonts-hanazono \
        fonts-khmeros \
        fonts-lao \
        fonts-sil-abyssinica \
        fonts-sil-ezra \
        fonts-sil-padauk \
        fonts-sil-scheherazade \
        fonts-thai-tlwg \
        fonts-lklug-sinhala \
        fonts-kacst \
        fonts-kacst-one \
        fonts-farsiweb \
        fonts-smc-anjalioldlipi \
        fonts-smc-chilanka \
        fonts-smc-dyuthi \
        fonts-smc-karumbi \
        fonts-smc-keraleeyam \
        fonts-smc-manjari \
        fonts-smc-meera \
        fonts-smc-rachana \
        fonts-smc-raghumalayalamsans \
        fonts-smc-suruma \
        fonts-smc-uroob \
        fonts-yrsa-rasa \
        fonts-cantarell \
        fonts-comfortaa \
        fonts-croscore \
        fonts-ebgaramond \
        fonts-fantasque-sans \
        fonts-junicode \
        fonts-lyx \
        fonts-mathjax \
        fonts-nanum \
        fonts-nanum-coding \
        fonts-nanum-extra \
        fonts-opensymbol \
        fonts-quicksand \
        fonts-sil-gentium \
        fonts-sil-gentiumplus \
        fonts-stix \
        fonts-texgyre \
        fonts-terminus \
        fonts-dejavu-mono \
        fonts-linuxlibertine \
        fonts-arkpandora \
        fonts-beteckna \
        fonts-gfs-artemisia \
        fonts-gfs-complutum \
        fonts-gfs-didot \
        fonts-gfs-neohellenic \
        fonts-gfs-olga \
        fonts-gfs-solomos \
        fonts-gfs-theokritos \
        fonts-liberation \
        fonts-dejavu-core

# python deps
COPY src/requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir --no-compile --break-system-packages -r /tmp/requirements.txt && \
    pip3 install --no-cache-dir --no-compile --break-system-packages --ignore-installed setuptools>=78.1.1 wheel>=0.46.2 && \
    apt-get remove --autoremove --purge -y python3-setuptools python3-wheel software-properties-common && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

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