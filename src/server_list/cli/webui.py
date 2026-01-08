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

import atexit
import logging
import os
from pathlib import Path

import flask
import flask_cors

# Base directory for images
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
IMG_DIR = BASE_DIR / "img"

import my_lib.webapp.base
import my_lib.webapp.config
import my_lib.webapp.event

from server_list.spec.webapi.cpu import cpu_api
from server_list.spec.webapi.config import config_api
from server_list.spec.webapi.vm import vm_api
from server_list.spec.webapi.uptime import uptime_api
from server_list.spec import data_collector, cache_manager
from server_list.spec.data_collector import start_collector, stop_collector
from server_list.spec.cache_manager import start_cache_worker, stop_cache_worker

URL_PREFIX = "/server-list"


def create_app(config: my_lib.webapp.config.WebappConfig) -> flask.Flask:
    my_lib.webapp.config.URL_PREFIX = URL_PREFIX
    my_lib.webapp.config.init(config)

    app = flask.Flask("server-list")

    # NOTE: アクセスログは無効にする
    logging.getLogger("werkzeug").setLevel(logging.ERROR)

    flask_cors.CORS(app)

    # Register API blueprints
    app.register_blueprint(cpu_api, url_prefix=f"{URL_PREFIX}/api")
    app.register_blueprint(config_api, url_prefix=f"{URL_PREFIX}/api")
    app.register_blueprint(vm_api, url_prefix=f"{URL_PREFIX}/api")
    app.register_blueprint(uptime_api, url_prefix=f"{URL_PREFIX}/api")

    # Register webapp blueprints
    app.register_blueprint(my_lib.webapp.base.blueprint_default)
    app.register_blueprint(my_lib.webapp.base.blueprint, url_prefix=URL_PREFIX)
    app.register_blueprint(my_lib.webapp.event.blueprint, url_prefix=URL_PREFIX)

    # SPA fallback route - return index.html for client-side routing
    @app.route(f"{URL_PREFIX}/machine/<path:subpath>")
    def spa_fallback(subpath):  # noqa: ARG001
        return flask.send_from_directory(
            my_lib.webapp.config.STATIC_DIR_PATH,
            "index.html"
        )

    # Serve server model images
    @app.route(f"{URL_PREFIX}/api/img/<path:filename>")
    def serve_image(filename):
        return flask.send_from_directory(IMG_DIR, filename)

    # Disable caching for API responses
    @app.after_request
    def add_no_cache_headers(response):
        if "/api/" in flask.request.path and "/api/img/" not in flask.request.path:
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

    # Initialize databases (required for API to work)
    cache_manager.init_db()
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

    import docopt
    import my_lib.config
    import my_lib.logger

    args = docopt.docopt(__doc__)

    config_file = args["-c"]
    port = int(args["-p"])
    debug_mode = args["-D"]

    my_lib.logger.init("server-list", level=logging.DEBUG if debug_mode else logging.INFO)

    config = my_lib.config.load(config_file, pathlib.Path("schema/config.schema"))

    webapp_config = my_lib.webapp.config.WebappConfig.from_dict(config["webapp"])

    app = create_app(webapp_config)

    app.config["CONFIG"] = config

    app.run(host="0.0.0.0", port=port, debug=debug_mode)  # noqa: S104


if __name__ == "__main__":
    main()
