#
# stage 1 - install shared lib
#

FROM ubuntu:24.04 AS lib-builder

# NOTE: this allows building the application with a specific library version
ARG LIBRARY_BRANCH=main

WORKDIR /build

RUN apt-get update && \
    apt-get -y install git python3-venv
RUN git clone -b $LIBRARY_BRANCH \
        https://github.com/not-mt/nmt-fastapi-library.git \
        /build

# build shared library as a wheel package
RUN python3 -m venv /build/venv && \
    . /build/venv/bin/activate && \
    pip install --upgrade pip && \
    pip install poetry && \
    poetry build -f wheel

#
# stage 2 - build Python environment
#

FROM ubuntu:24.04 AS app-builder

WORKDIR /build

RUN apt-get update && \
    apt-get -y install python3-venv

# copy shared library
COPY --from=lib-builder /build/dist /library_wheels

# copy application code
COPY src /build/src
COPY alembic /build/alembic
COPY alembic.ini /build/
COPY LICENSE /build/
COPY README.md /build/
COPY nmtfast-config-default.yaml /build/
COPY samples/poetry.toml /build/
COPY pyproject.toml /build/
COPY poetry.lock /build/
COPY poetry.toml /build/

# build app as a wheel package
RUN python3 -m venv /build/venv && \
    . /build/venv/bin/activate && \
    pip install --upgrade pip && \
    pip install poetry && \
    poetry config virtualenvs.create false && \
    pip install /library_wheels/*.whl && \
    poetry build -f wheel

#
# stage 3 - final image
#

FROM ubuntu:24.04

LABEL maintainer="Alexander Haye <ahayehaye@not-mt.dev>"

ARG APP_UID=5001
ARG APP_GID=5001
ENV TZ=Etc/UTC
ENV VIRTUAL_ENV=/app/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# install only runtime deps
RUN apt-get update && \
    apt-get -y install \
        python3-venv \
        nginx \
        supervisor \
        procps \
        psmisc && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# create app user and dirs
RUN groupadd -g $APP_GID app && \
    useradd -m -d /app -s /bin/bash \
        -u $APP_UID -g $APP_GID app && \
    mkdir src /app/static

# copy shared library from stage 1 and app fromm stage 2
COPY --from=lib-builder /build/dist /app/dist
COPY --from=app-builder /build/dist /app/dist

# copy pyproject.toml file, which is needed to load OpenAPI schema
COPY --from=app-builder /build/pyproject.toml /app/pyproject.toml

# build venv, install packages build in earlier stages
RUN python3 -m venv /app/venv && \
    . /app/venv/bin/activate && \
    pip install --upgrade pip && \
    pip install /app/dist/*.whl

# copy entrypoint, nginx, and supervisor config
# NOTE: /app is writable by the unprivileged user, but the source code
#   should NOT be possible to edit once the container is running
COPY nmtfast-config-default.yaml /app/nmtfast-config-default.yaml
COPY docker/nginx.conf /etc/nginx/nginx.conf
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod 755 /entrypoint.sh && \
    chown app:app /run /app

# switch to app user and start the app
USER app:app
WORKDIR /app
EXPOSE 8080
ENTRYPOINT ["/entrypoint.sh"]
