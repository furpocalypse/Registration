# Docker Compose Example

This is a Docker Compose configuration to run a full registration service. It is
intended as a demo and as a starting point for a proper production configuration, it
should not be directly used in production.

Make sure you have recursively cloned all submodules in this repository.

**Permissions Caveat**: Because configuration files are bind mounted into the
containers, their permissions in the host filesystem need to be set appropriately:

- `config.yml`, `events.yml` - readable by UID or GID 1000
- `config.json` - readable by UID or GID 101

Start the service with `docker compose up`. This will build the container images and
create the containers. You can view the example at
`https://localhost/events/example-event`

Stop and remove the service with `docker compose down` and `docker compose rm`.
