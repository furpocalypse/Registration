"""Web application module."""
import argparse
from ipaddress import IPv4Network, IPv6Network
from pathlib import Path

import uvicorn
from blacksheep import Application, Content, HTTPException, Response
from blacksheep.plugins import json
from blacksheep.server.remotes.forwarding import XForwardedHeadersMiddleware
from guardpost import Policy
from guardpost.common import AuthenticatedRequirement
from oes.registration.auth import TokenAuthHandler
from oes.registration.config import load_config, load_event_config
from oes.registration.database import (
    DBConfig,
    db_session_factory,
    db_session_middleware,
)
from oes.registration.docs import docs
from oes.registration.http_client import setup_http_client, shutdown_http_client
from oes.registration.log import setup_logging
from oes.registration.payment.config import load_services
from oes.registration.serialization import get_converter
from oes.registration.serialization.json import json_dumps, json_loads
from oes.registration.services.access_code import AccessCodeService
from oes.registration.services.auth import AuthService
from oes.registration.services.cart import CartService
from oes.registration.services.checkout import CheckoutService
from oes.registration.services.event import EventService
from oes.registration.services.hook import HookRetryService
from oes.registration.services.interview import InterviewService
from oes.registration.services.registration import RegistrationService
from oes.registration.views.responses import BodyValidationError, ExceptionDetails
from sqlalchemy.ext.asyncio import AsyncSession

app = Application()

docs.bind_app(app)

json.use(
    loads=json_loads,
    dumps=lambda o: json_dumps(o).decode(),  # :(
)

app.services.add_scoped(AuthService)
app.services.add_scoped(EventService)
app.services.add_scoped(RegistrationService)
app.services.add_scoped(CartService)
app.services.add_scoped(CheckoutService)
app.services.add_scoped(InterviewService)
app.services.add_scoped(AccessCodeService)


async def validation_error_handler(app, request, exc: BodyValidationError):
    return Response(
        422,
        content=Content(
            content_type=b"application/json",
            data=get_converter().dumps(ExceptionDetails.create(exc.exc)),
        ),
    )


async def conflict_error_handler(app, request, exc: HTTPException):
    if len(exc.args) == 1 and isinstance(exc.args[0], str):
        return Response(
            exc.status,
            content=Content(
                content_type=b"application/json",
                data=get_converter().dumps(
                    ExceptionDetails(
                        detail=exc.args[0],
                    )
                ),
            ),
        )


app.exceptions_handlers[BodyValidationError] = validation_error_handler
app.exceptions_handlers[409] = conflict_error_handler
app.middlewares.append(db_session_middleware)

authorization = app.use_authorization()
authorization.default_policy = Policy("authenticated", AuthenticatedRequirement())


#
@app.on_middlewares_configuration
def configure_forwarded_headers(app: Application):
    app.middlewares.insert(
        0,
        XForwardedHeadersMiddleware(
            # Allow X-Forwarded headers from private networks
            known_networks=[
                IPv4Network("127.0.0.0/8"),
                IPv4Network("10.0.0.0/8"),
                IPv4Network("172.16.0.0/12"),
                IPv4Network("192.168.0.0/16"),
                IPv6Network("fc00::/7"),
                IPv6Network("::1/128"),
            ]
        ),
    )


@app.on_start
async def setup_app(app: Application):
    # TODO: specify paths
    config = load_config(Path("config.yml"))
    events = load_event_config(Path("events.yml"))
    app.services.add_instance(config)
    app.services.add_instance(events)

    db_config = DBConfig.create(config.database.url)
    app.services.add_instance(db_config)
    app.services.add_scoped_by_factory(db_session_factory, AsyncSession)

    # TODO: remove
    await db_config.create_tables()

    http_client = setup_http_client()
    app.services.add_instance(http_client)

    app.services.add_instance(HookRetryService(db_config))

    payment_services = load_services(config.payment)
    app.services.add_instance(payment_services)


@app.on_stop
async def shutdown_app(app: Application):
    await app.service_provider[HookRetryService].close()
    await shutdown_http_client()

    db_config: DBConfig = app.service_provider[DBConfig]
    await db_config.close()


def parse_args():
    """Parse command line arguments."""

    # maybe look at different parsers in the future
    parser = argparse.ArgumentParser(
        description="OES Registration HTTP API server",
    )

    parser.add_argument(
        "-p", "--port", type=int, help="the port to listen on", default=8000
    )
    parser.add_argument(
        "-b", "--bind", type=str, help="the address to bind to", default="127.0.0.1"
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="enable debug settings and logging",
        default=False,
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="watch file changes and reload the server for development",
        default=False,
    )

    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        help="path to the config file",
        default=Path("config.yml"),
    )

    parser.add_argument(
        "--events",
        type=Path,
        help="path to the events config file",
        default=Path("events.yml"),
    )

    return parser.parse_args()


def app_factory():
    """Set up and return the ASGI app."""

    # There's no way to pass settings from the main uvicorn process to the worker
    # processes, but we can just parse the command line arguments again
    args = parse_args()

    # TODO: pass the config to the app so we don't have to parse it twice
    config = load_config(Path("config.yml"))

    # set up logging
    setup_logging(debug=args.debug)

    # setup authentication
    app.use_authentication().add(TokenAuthHandler(config))

    # set up CORS

    app.use_cors(
        allow_methods=("GET", "POST", "PUT", "DELETE"),
        allow_origins=config.auth.allowed_origins,
        allow_headers=(
            "Authorization",
            "Content-Type",
        ),
    )

    return app


def run():
    """Entry point for the console script."""

    args = parse_args()

    if args.reload:
        # for reload to work we have to run in single-worker mode
        uvicorn.run(
            "oes.registration.app:app_factory",
            factory=True,
            host=args.bind,
            port=args.port,
            reload=True,
            workers=1,
        )
    else:
        uvicorn.run(
            "oes.registration.app:app_factory",
            factory=True,
            host=args.bind,
            port=args.port,
        )


# Import views

import oes.registration.views.access_code  # noqa
import oes.registration.views.auth  # noqa
import oes.registration.views.cart  # noqa
import oes.registration.views.checkout  # noqa
import oes.registration.views.event  # noqa
import oes.registration.views.registration  # noqa
import oes.registration.views.selfservice  # noqa
