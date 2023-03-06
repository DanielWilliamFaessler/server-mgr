# syntax=docker/dockerfile:1

FROM python:3.11 as base

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
    && apt-get install -y \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LO https://releases.hashicorp.com/terraform/1.3.9/terraform_1.3.9_linux_amd64.zip \
    && unzip terraform_1.3.9_linux_amd64.zip \
    && install -o root -g root -m 0755 terraform /usr/local/bin/terraform

RUN curl -LO "https://dl.k8s.io/release/v1.26.0/bin/linux/amd64/kubectl" \
  && curl -LO "https://dl.k8s.io/release/v1.26.0/bin/linux/amd64/kubectl.sha256" \
  && echo "$(cat kubectl.sha256) kubectl" | sha256sum --check --quiet --strict \
  && install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

ENV PROJECT_FOLDER=app

ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_VERSION_SMALLER_AS=2 \
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app

### latest dockerize version
RUN wget -O - $(wget -O - https://api.github.com/repos/powerman/dockerize/releases/latest | grep -i /dockerize-$(uname -s)-$(uname -m)\" | cut -d\" -f4) | install /dev/stdin /usr/local/bin/dockerize

RUN pip install "poetry<$POETRY_VERSION_SMALLER_AS"

ADD ./poetry.lock ./pyproject.toml /app/

FROM base as dev

RUN poetry install --no-interaction --no-ansi

WORKDIR /app/${PROJECT_FOLDER}

FROM base as deploy

ADD ./ /app/

WORKDIR /app/${PROJECT_FOLDER}

RUN poetry install --no-dev --no-interaction --no-ansi
