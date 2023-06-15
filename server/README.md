# OES Registration HTTP API

The HTTP API for the registration software.

## Development Setup

- Install the development environment with [Poetry](https://python-poetry.org/):

      poetry install

- Install [pre-commit](https://pre-commit.com/) and run:

      pre-commit install

  to configure the linting/formatting hooks.

- Run tests with `poetry run pytest`.

## Configuration

- Copy `config.example.yml` to `config.yml` and edit the settings appropriately.
- Copy `events.example.yml` to `events.yml` and configure an event.

## Database Migrations

Run database migrations with `poetry run alembic upgrade head`.

You can run the migrations using the Docker image like:

    docker run --rm <bind mounts> --entrypoint alembic <image id> upgrade head
