FROM python:3.11-slim

RUN --mount=type=cache,target=/var/cache/apt \
    apt-get update -y \
    && apt-get install -y \
    mediainfo

# set environment variables
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV POETRY_VERSION=1.7.1

# install poetry
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip \
    && pip install "poetry==$POETRY_VERSION" \
    && poetry config virtualenvs.create false

# set work directory as /deovr-json-gen
WORKDIR /deovr-json-gen

# install dependencies
COPY poetry.lock* pyproject.toml /deovr-json-gen/
RUN --mount=type=cache,target=/root/.cache/pip \
    poetry install --with=dev --no-interaction

# copy script
COPY main.py .

# run script with /tmp/vr as directory
CMD ["python", "main.py", "/tmp/vr"]
