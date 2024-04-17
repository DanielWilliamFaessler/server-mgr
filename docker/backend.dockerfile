# syntax=docker/dockerfile:1

# switch to official version when https://github.com/python-poetry/poetry/issues/4036 is resolved
FROM mateusoliveira43/poetry:1.4.1-python3.11.2-bullseye as base

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
    && apt-get install -y \
    wget \
    curl \
    super \
    gosu \
    && rm -rf /var/lib/apt/lists/* \
    # verify that the binary works
	gosu nobody true

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
    VIRTUALENV_ALWAYS_COPY=1

### latest dockerize version
# RUN wget -O - $(wget -O - https://api.github.com/repos/powerman/dockerize/releases/latest | grep -i /dockerize-$(uname -s)-$(uname -m)\" | cut -d\" -f4) | install /dev/stdin /usr/local/bin/dockerize
## Specific dockerize version
RUN curl -sfL https://github.com/powerman/dockerize/releases/download/v0.19.0/dockerize-`uname -s`-`uname -m` | install /dev/stdin /usr/local/bin/dockerize

ENV POETRY_CACHE_DIR=/app/.cache USERNAME=py HOME=/app WORKDIR=/app/${PROJECT_FOLDER}
RUN mkdir -p ${POETRY_CACHE_DIR}

WORKDIR ${WORKDIR}

# Add volume
VOLUME /Terraform_Workspaces

ADD entrypoint.sh /entrypoint/entrypoint.sh

RUN useradd -s /bin/bash --no-create-home --gid 100 -d ${HOME} ${USERNAME}

ENTRYPOINT ["/entrypoint/entrypoint.sh"]

# DEVELOPMENT
FROM base as dev

# USER ${USERNAME}

# PRODUCTION
FROM base as prod

ADD --chown=${USERNAME}:100 ./poetry.lock ./pyproject.toml /app/

RUN poetry install --no-interaction --no-ansi --no-root

ADD --chown=${USERNAME}:100 . /app/
