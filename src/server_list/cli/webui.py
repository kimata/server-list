#!/usr/bin/env python3
"""
Flask application to serve the Server List React app at /server-list

Usage:
  server-list [-c CONFIG] [-p PORT] [-D]

Options:
  -c CONFIG         : CONFIG を設定ファイルとして読み込んで実行します。[default: config.yaml]
  -p PORT           : WEB サーバのポートを指定します。[default: 5000]
  -D                : デバッグモードで動作します。
"""

from __future__ import annotations

import atexit
import logging
import os
import signal
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import unquote

import flask
import flask_cors
import my_lib.webapp.base
import my_lib.webapp.config
import my_lib.webapp.event
import my_lib.webapp.util

from server_list.spec import cache_manager, cpu_benchmark, data_collector, db
from server_list.spec.cache_manager import start_cache_worker, stop_cache_worker
from server_list.spec.data_collector import start_collector, stop_collector
from server_list.spec.ogp import (
    generate_machine_page_ogp,
    generate_top_page_ogp,
    inject_ogp_into_html,
)
from server_list.spec.webapi.config import config_api
from server_list.spec.webapi.cpu import cpu_api
from server_list.spec.webapi.power import power_api
from server_list.spec.webapi.storage import storage_api
from server_list.spec.webapi.uptime import uptime_api
from server_list.spec.webapi.vm import vm_api

if TYPE_CHECKING:
    from server_list.config import Config

URL_PREFIX = "/server-list"


def term() -> None:
    """Terminate the application gracefully."""
    logging.info("Terminating application...")
    stop_cache_worker()
    stop_collector()
    logging.info("Application terminated.")


def sig_handler(num: int, frame) -> None:  # noqa: ARG001
    """Handle signals for graceful shutdown."""
    logging.warning("Received signal %d", num)

    if num in (signal.SIGTERM, signal.SIGINT):
        term()


def create_app(
    webapp_config: my_lib.webapp.config.WebappConfig,
    config: Config | None = None,
) -> flask.Flask:
    my_lib.webapp.config.URL_PREFIX = URL_PREFIX
    my_lib.webapp.config.init(webapp_config)

    # Initialize paths from config
    if config:
        db.init_from_config(config)

    app = flask.Flask("server-list")

    # NOTE: アクセスログは無効にする
    logging.getLogger("werkzeug").setLevel(logging.ERROR)

    flask_cors.CORS(app)

    # Register API blueprints
    app.register_blueprint(cpu_api, url_prefix=f"{URL_PREFIX}/api")
    app.register_blueprint(config_api, url_prefix=f"{URL_PREFIX}/api")
    app.register_blueprint(vm_api, url_prefix=f"{URL_PREFIX}/api")
    app.register_blueprint(uptime_api, url_prefix=f"{URL_PREFIX}/api")
    app.register_blueprint(power_api, url_prefix=f"{URL_PREFIX}/api")
    app.register_blueprint(storage_api, url_prefix=f"{URL_PREFIX}/api")

    # Register webapp blueprints
    app.register_blueprint(my_lib.webapp.base.blueprint_default)
    app.register_blueprint(my_lib.webapp.base.blueprint, url_prefix=URL_PREFIX)
    app.register_blueprint(my_lib.webapp.event.blueprint, url_prefix=URL_PREFIX)
    app.register_blueprint(my_lib.webapp.util.blueprint, url_prefix=URL_PREFIX)

    def get_base_url() -> str:
        """Get base URL from request."""
        return flask.request.url_root.rstrip("/")

    def serve_html_with_ogp(ogp_tags: str) -> flask.Response:
        """Serve index.html with OGP tags injected."""
        static_dir = my_lib.webapp.config.STATIC_DIR_PATH
        if static_dir is None:
            return flask.Response("Static directory not configured", status=500)
        index_path = Path(static_dir) / "index.html"
        if not index_path.exists():
            return flask.send_from_directory(static_dir, "index.html")

        html_content = index_path.read_text(encoding="utf-8")
        modified_html = inject_ogp_into_html(html_content, ogp_tags)
        return flask.Response(modified_html, mimetype="text/html")

    # Top page with OGP
    @app.route(f"{URL_PREFIX}/")
    def index_with_ogp():
        ogp_tags = generate_top_page_ogp(get_base_url(), config)
        return serve_html_with_ogp(ogp_tags)

    # SPA fallback route with machine-specific OGP
    @app.route(f"{URL_PREFIX}/machine/<path:machine_name>")
    def machine_page_with_ogp(machine_name: str):
        decoded_name = unquote(machine_name)
        ogp_tags = generate_machine_page_ogp(
            get_base_url(),
            decoded_name,
            config,
            db.IMAGE_DIR,
        )
        return serve_html_with_ogp(ogp_tags)

    # Serve server model images
    @app.route(f"{URL_PREFIX}/api/img/<path:filename>")
    def serve_image(filename):
        return flask.send_from_directory(db.IMAGE_DIR, filename)

    # Initialize databases (required for API to work)
    cache_manager.init_db()
    cpu_benchmark.init_db()
    data_collector.init_db()

    # Start background workers
    # - In debug mode with reloader: WERKZEUG_RUN_MAIN == "true" in the main worker process
    # - In non-debug mode: WERKZEUG_RUN_MAIN is not set
    werkzeug_run_main = os.environ.get("WERKZEUG_RUN_MAIN")
    if werkzeug_run_main == "true" or werkzeug_run_main is None:
        start_cache_worker()
        start_collector()
        atexit.register(stop_cache_worker)
        atexit.register(stop_collector)

    my_lib.webapp.config.show_handler_list(app)

    return app


def main() -> None:
    import pathlib
    import sys
    import traceback

    import docopt
    import my_lib.logger
    import my_lib.webapp.config

    from server_list.config import Config

    assert __doc__ is not None
    args = docopt.docopt(__doc__)

    config_file = args["-c"]
    port = int(args["-p"])
    debug_mode = args["-D"]

    my_lib.logger.init("server-list", level=logging.DEBUG if debug_mode else logging.INFO)

    logging.info("Starting server-list webui...")
    logging.info("Config file: %s", config_file)
    logging.info("Port: %s, Debug: %s", port, debug_mode)

    # Use cwd-relative schema path (works for both source and Docker)
    schema_path = pathlib.Path("schema/config.schema")
    if not schema_path.exists():
        # Fall back to db.CONFIG_SCHEMA_PATH for source tree
        schema_path = db.CONFIG_SCHEMA_PATH
    logging.info("Schema path: %s (exists: %s)", schema_path, schema_path.exists())

    try:
        config = Config.load(pathlib.Path(config_file), schema_path)
        logging.info("Config loaded successfully, %d machines defined", len(config.machine))

        webapp_config = my_lib.webapp.config.WebappConfig.parse({
            "static_dir_path": config.webapp.static_dir_path,
        })

        app = create_app(webapp_config, config=config)

        app.config["CONFIG"] = config

        signal.signal(signal.SIGTERM, sig_handler)

        app.run(host="0.0.0.0", port=port, debug=debug_mode)  # noqa: S104
    except KeyboardInterrupt:
        logging.info("Received KeyboardInterrupt, shutting down...")
        sig_handler(signal.SIGINT, None)
    except Exception:
        logging.exception("Fatal error during application startup")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
