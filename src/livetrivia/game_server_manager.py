"""Unified game-server lifecycle abstraction.

Provides a common async interface for spawning, stopping, and cleaning up
ephemeral game-server processes.  Two concrete backends exist:

* :class:`DockerGameServerManager` — wraps the existing Docker-outside-of-Docker
  helpers in :mod:`livetrivia.docker_manager`.
* :class:`K8sGameServerManager` — creates Kubernetes Pods, Services, and
  ConfigMaps via ``kubernetes_asyncio`` (see :mod:`livetrivia.k8s_manager`).

Which backend is used is determined by the ``DEPLOYMENT_MODE`` environment
variable (``"docker"`` or ``"kubernetes"``).  The active manager is injected as
a FastAPI dependency — see :data:`livetrivia.db.GameServerDep`.
"""

from __future__ import annotations

import asyncio
import typing_extensions as tp


class GameServerManager(tp.Protocol):
    """Protocol that both Docker and Kubernetes backends satisfy."""

    async def spawn_game_server(
        self, game_code: str, file_bytes: bytes, game_id: str
    ) -> None: ...

    async def stop_game_server(self, game_code: str) -> None: ...

    async def stop_all_game_servers(self) -> None: ...


class DockerGameServerManager:
    """Delegates to the synchronous helpers in :mod:`livetrivia.docker_manager`,
    running them in a thread so the async event-loop is never blocked."""

    async def spawn_game_server(
        self, game_code: str, file_bytes: bytes, game_id: str
    ) -> None:
        from livetrivia.docker_manager import spawn_game_server

        await asyncio.to_thread(spawn_game_server, game_code, file_bytes, game_id)

    async def stop_game_server(self, game_code: str) -> None:
        from livetrivia.docker_manager import stop_game_server

        await asyncio.to_thread(stop_game_server, game_code)

    async def stop_all_game_servers(self) -> None:
        from livetrivia.docker_manager import stop_all_game_servers

        await asyncio.to_thread(stop_all_game_servers)
