FROM python:3.11-slim AS python-image

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked apt-get update -y \
    && apt-get install -y --no-install-recommends --no-install-suggests \
    mediainfo

# set environment variables
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV POETRY_VERSION=1.7.1

WORKDIR /requirements
# copy over the files needed for poetry
COPY poetry.lock* pyproject.toml ./

# install poetry, export requirements
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install "poetry==$POETRY_VERSION" \
    && poetry export --without dev --without-hashes -f requirements.txt --output requirements.txt

# create a virtual environment and install dependencies
RUN python -m venv --copies /venv
# set python to use the virtual environment
ENV PATH="/venv/bin:$PATH"
# install dependencies to the virtual environment
RUN --mount=type=cache,target=/root/.cache/pip \
    /venv/bin/python -m pip install -r requirements.txt


FROM nginx:1.25-bookworm

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked apt-get update -y \
    && apt-get install -y --no-install-recommends --no-install-suggests \
    # since we copied over the venv, we need to install shared python libraries
    libpython3-dev \
    # mediainfo is a dependency of deovr json generator used by pymediainfo
    mediainfo \
    # clean up and remove apt lists
    && rm -rf /var/lib/apt/lists/*

# copy over the python virtual environment
COPY --from=python-image /venv /venv
# set python to use the virtual environment
ENV PATH="/venv/bin:$PATH"
# set python as default python
RUN update-alternatives --install /usr/bin/python3 python3 /venv/bin/python 1 \
    && update-alternatives --install /usr/bin/python python /venv/bin/python 1

# set environment variables
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

COPY nginx.conf /etc/nginx/nginx.conf

COPY docker_start.sh /docker_start.sh
RUN sed -i "s/\r$//g" /docker_start.sh \
    && chmod +x /docker_start.sh

# copy script
COPY main.py /deovr-json-gen/

WORKDIR /usr/share/nginx/html

CMD ["/docker_start.sh"]
