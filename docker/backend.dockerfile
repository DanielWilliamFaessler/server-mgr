# syntax=docker/dockerfile:1

FROM python:3.11 as base

# ENV DEBIAN_FRONTEND=noninteractive
# RUN apt-get update \
#     && apt-get install -y \
#     && rm -rf /var/lib/apt/lists/*

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
