FROM ubuntu:24.04@sha256:7a398144c5a2fa7dbd9362e460779dc6659bd9b19df50f724250c62ca7812eb3

RUN --mount=type=cache,target=/var/lib/apt,sharing=locked \
    --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install --no-install-recommends --assume-yes \
    curl \
    ca-certificates \
    tini \
    build-essential \
    git \
    language-pack-ja \
    tzdata

ENV TZ=Asia/Tokyo \
    LANG=ja_JP.UTF-8 \
    LANGUAGE=ja_JP:ja \
    LC_ALL=ja_JP.UTF-8

RUN locale-gen en_US.UTF-8
RUN locale-gen ja_JP.UTF-8

USER ubuntu

ENV PYTHONDONTWRITEBYTECODE=1
ENV PATH="/home/ubuntu/.local/bin:$PATH"
ENV UV_LINK_MODE=copy

# ubuntu ユーザーで uv をインストール
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

WORKDIR /opt/server-list

RUN --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=.python-version,target=.python-version \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=README.md,target=README.md \
    --mount=type=bind,source=src,target=src \
    --mount=type=cache,target=/home/ubuntu/.cache/uv,uid=1000,gid=1000 \
    uv sync --no-editable --no-group dev

ARG IMAGE_BUILD_DATE
ENV IMAGE_BUILD_DATE=${IMAGE_BUILD_DATE}

COPY --chown=ubuntu:ubuntu . .

RUN mkdir -p data

EXPOSE 5000

ENTRYPOINT ["/usr/bin/tini", "--", "uv", "run", "--no-group", "dev"]

CMD ["server-list-webui"]
