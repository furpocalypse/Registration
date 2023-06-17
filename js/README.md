# OES Registration Web Interface

The web interface for the registration service.

The application is built with React and TypeScript. It is bundled using Webpack into an
entirely client-side bundle, with no server-side rendering. Data is fetched and updated
using the registration HTTP API.

## Development Setup

- Install an up to date Node.js.

- Install the dependencies by running:

      npm install

- Install [pre-commit](https://pre-commit.com/) and run:

      pre-commit install

  to configure the linting/formatting hooks.

- Start a development server with `npm start`.

- Build the production bundle with `npm run build`.

You can add simulated latency with the `DELAY` environment variable like `DELAY=1000 npm start`

## Configuration

- Copy `config.example.json` to `config.json` and edit the settings:
  - `apiUrl` - the base URL of the HTTP API
- Copy `theme.example.ts` to `theme.ts` to customize the theme and override styles and
  default properties.

## Deploying

After building the production bundle, copy the files from `dist/` into a public
directory for your web server. HTTPS must be enabled.

Any filenames matching `.+\.[a-f0-9]{20}\..+` include a hash of their content, and may
have a long cache time. `index.html` should have a `max-age` of `0`.

It is recommended to set a strict [Content Security Policy
(CSP)](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP) for this site.

## Container Image

A container image can be built that serves the web application files using a minimally
configured web server (`nginx`). When using this method, the container must not be
accessible to the internet; all requests must be proxied through from a properly
configured web server. The included web server listens on port 9000.

Build the container image with Docker:

    docker build -t oes-registration-client .

Run a test container:

    docker run --rm -t -p 9000:9000 oes-registration-client
