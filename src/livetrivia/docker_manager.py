"""Docker-outside-of-Docker (DooD) manager for spawning and stopping game
server containers from within the API container.

The API container must have ``/var/run/docker.sock`` mounted as a volume so it
can communicate with the host Docker daemon.

Environment variables
---------------------
DOCKER_NETWORK
    Docker network to attach spawned containers to.
    Default: ``livetrivia_net``
GAME_IMAGE
    Docker image used for game server containers.
    Default: ``livetrivia-game:latest``
NGINX_CONTAINER_NAME
    Name of the nginx container to signal after config changes.
    Default: ``livetrivia_nginx``
"""

import os

import docker
import docker.errors

from livetrivia.nginx_config import remove_game_route, write_game_route

DOCKER_NETWORK: str = os.getenv("DOCKER_NETWORK", "livetrivia_net")
GAME_IMAGE: str = os.getenv("GAME_IMAGE", "livetrivia-game:latest")
NGINX_CONTAINER_NAME: str = os.getenv("NGINX_CONTAINER_NAME", "livetrivia_nginx")


def _client() -> docker.DockerClient:
    return docker.from_env()


def container_name_for_game(game_code: str) -> str:
    return f"gameserver_{game_code}"


def spawn_game_server(game_code: str) -> None:
    """Start a game server container for *game_code*.

    If a container with the expected name already exists but is stopped it will
    be started instead of creating a duplicate.  After the container is
    running the nginx location config is written and nginx is reloaded so the
    route becomes live.
    """
    client = _client()
    name = container_name_for_game(game_code)

    try:
        container = client.containers.get(name)
        if container.status != "running":
            container.start()
    except docker.errors.NotFound:
        client.containers.run(
            GAME_IMAGE,
            name=name,
            network=DOCKER_NETWORK,
            detach=True,
            labels={
                "managed-by": "livetrivia-api",
                "game-code": game_code,
            },
        )

    write_game_route(game_code)
    _reload_nginx()


def stop_game_server(game_code: str) -> None:
    """Stop and remove the game server container for *game_code*, then clean up
    its nginx route and reload nginx."""
    client = _client()
    name = container_name_for_game(game_code)

    try:
        container = client.containers.get(name)
        container.stop(timeout=5)
        container.remove()
    except docker.errors.NotFound:
        pass

    remove_game_route(game_code)
    _reload_nginx()


def _reload_nginx() -> None:
    """Send SIGHUP to the nginx container so it gracefully reloads its config."""
    client = _client()
    try:
        container = client.containers.get(NGINX_CONTAINER_NAME)
        container.kill(signal="SIGHUP")
    except docker.errors.NotFound:
        pass
