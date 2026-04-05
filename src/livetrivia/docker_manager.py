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
COMPOSE_PROJECT_NAME
    Docker Compose project name to stamp on spawned containers so that
    ``docker compose down --remove-orphans`` cleans them up automatically.
    Default: ``bintrong_game``
"""

import io
import os
import tarfile

import docker
import docker.errors

from livetrivia.nginx_config import remove_game_route, write_game_route

DOCKER_NETWORK: str = os.getenv("DOCKER_NETWORK", "livetrivia_net")
GAME_IMAGE: str = os.getenv("GAME_IMAGE", "livetrivia-game:latest")
NGINX_CONTAINER_NAME: str = os.getenv("NGINX_CONTAINER_NAME", "livetrivia_nginx")
COMPOSE_PROJECT_NAME: str = os.getenv("COMPOSE_PROJECT_NAME", "bintrong_game")


def _client() -> docker.DockerClient:
    return docker.from_env()


def container_name_for_game(game_code: str) -> str:
    return f"gameserver_{game_code}"


def _make_tar(data: bytes, filename: str = "questions.apkg") -> bytes:
    """Wrap *data* in an in-memory tar archive named *filename*."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        info = tarfile.TarInfo(name=filename)
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def spawn_game_server(game_code: str, file_bytes: bytes) -> None:
    """Start a game server container for *game_code*.

    *file_bytes* are the raw bytes of the Anki package to inject into the
    container at ``/app/questions.apkg`` before it starts.  The file is
    delivered via ``put_archive`` so no host-filesystem path is required
    (safe for Docker-outside-of-Docker deployments).

    If a container with the expected name already exists but is stopped it will
    have the file re-injected and be restarted.  After the container is
    running the nginx location config is written and nginx is reloaded so the
    route becomes live.
    """
    client = _client()
    name = container_name_for_game(game_code)
    tar_data = _make_tar(file_bytes)

    try:
        container = client.containers.get(name)
        if container.status != "running":
            container.put_archive("/app", tar_data)
            container.start()
    except docker.errors.NotFound:
        container = client.containers.create(
            GAME_IMAGE,
            # ports={3000:3000},
            name=name,
            network=DOCKER_NETWORK,
            detach=True,
            labels={
                "managed-by": "livetrivia-api",
                "game-code": game_code,
                "com.docker.compose.project": COMPOSE_PROJECT_NAME,
                "com.docker.compose.service": f"gameserver_{game_code}",
            },
        )
        container.put_archive("/app", tar_data)
        container.start()

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
