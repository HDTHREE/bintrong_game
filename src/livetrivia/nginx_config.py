"""Utility for building and writing nginx location configs for game servers.

The shared ``nginx_config`` Docker volume is mounted at ``/nginx_conf`` inside
the API container and at ``/etc/nginx/conf.d/games/`` inside the nginx
container.  The ``default.conf`` server block contains::

    include /etc/nginx/conf.d/games/*.conf;

so any ``.conf`` file written here is picked up on the next nginx reload.
"""

import os
import pathlib

NGINX_CONF_PATH: str = os.getenv("NGINX_CONF_PATH", "/nginx_conf")


def _conf_file(game_code: str) -> pathlib.Path:
    return pathlib.Path(NGINX_CONF_PATH) / f"{game_code}.conf"


def write_game_route(game_code: str) -> None:
    """Write a location block that proxies ``/gameserver/{game_code}/`` to the
    game server container."""
    conf_path = _conf_file(game_code)
    conf_path.parent.mkdir(parents=True, exist_ok=True)
    conf_path.write_text(
        f"location /gameserver/{game_code}/ {{\n"
        f"    proxy_pass http://gameserver_{game_code}:3000/;\n"
        f"    proxy_http_version 1.1;\n"
        f"    proxy_set_header Upgrade $http_upgrade;\n"
        f'    proxy_set_header Connection "upgrade";\n'
        f"    proxy_set_header Host $host;\n"
        f"    proxy_read_timeout 3600;\n"
        f"    proxy_send_timeout 3600;\n"
        f"}}\n"
    )


def remove_game_route(game_code: str) -> None:
    """Remove the location block for a stopped game server."""
    conf_file = _conf_file(game_code)
    if conf_file.exists():
        conf_file.unlink()
