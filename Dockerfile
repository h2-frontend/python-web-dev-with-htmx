# syntax=docker/dockerfile:1
# https://docs.docker.com/go/dockerfile-reference/

ARG PYTHON_VERSION=3.11.4
FROM python:${PYTHON_VERSION}-slim AS base

# unbuffered print & no .pyc 
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Create a non-privileged user that the app will run under.
# See https://docs.docker.com/go/dockerfile-user-best-practices/
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    appuser

RUN apt update && apt install parallel curl -y

# Download dependencies as a separate step to take advantage of Docker's caching.
# Leverage a cache mount to /root/.cache/pip to speed up subsequent builds.
# Leverage a bind mount to requirements.txt to avoid having to copy them into this layer.
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    python -m pip install -r requirements.txt

# tailwindcss binary should be downloaded separately due to permission issue
# tailwindcss binary installed from 'pip pytailwindcss' causes permission issue
RUN curl -sLO https://github.com/tailwindlabs/tailwindcss/releases/download/v3.4.3/tailwindcss-linux-x86 \
  && mv tailwindcss-linux-x86 tailwindcss && chmod +x tailwindcss

# Switch to the non-privileged user to run the application.
USER appuser

COPY . .
EXPOSE 8000
CMD python3 -m uvicorn app:app --host=0.0.0.0 --port=8000