FROM python:3.9.16-alpine3.18 AS python

FROM python AS build
RUN apk add git build-base
WORKDIR /build
RUN pip install --no-cache-dir poetry wheel
RUN python -m venv /app
COPY pyproject.toml poetry.lock ./
# hack: exclude oes-* dependencies due to git repos not having hashes
RUN poetry export -E stripe | grep -v ^oes- > requirements.txt
RUN pip wheel --no-cache-dir -w deps -r requirements.txt
RUN /app/bin/pip install --no-cache-dir deps/*
COPY src/ src/
RUN /app/bin/pip install --no-cache-dir .[stripe]

FROM python AS target
RUN adduser -h /app -H -D python \
    && mkdir /config
COPY --from=build /app/ /app/
WORKDIR /config
USER python
ENTRYPOINT ["/app/bin/oes-registration"]
