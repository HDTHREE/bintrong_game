"""Kubernetes backend for :class:`~livetrivia.game_server_manager.GameServerManager`.

Dynamically creates and tears down game-server **Pods**, **Services**, and
**ConfigMaps** via the ``kubernetes_asyncio`` client.  Nginx routing is managed
by exec'ing into the nginx pod to write/remove location-block config files and
issuing ``nginx -s reload``.

Environment variables
---------------------
K8S_NAMESPACE
    Namespace for spawned resources.  Default: ``default``.
GAME_IMAGE
    Container image for the game server pod.  Default: ``livetrivia-game:latest``.
BEARCAT_API_URL
    URL the game server uses to call back to the API.  Default: ``http://lt-api:8000``.
NGINX_POD_LABEL
    Label selector used to find the nginx pod for exec.
    Default: ``app.kubernetes.io/component=nginx``.
"""

from __future__ import annotations

import base64
import logging
import os

from kubernetes_asyncio import client as k8s, config as k8s_config
from kubernetes_asyncio.stream import WsApiClient

logger = logging.getLogger(__name__)

K8S_NAMESPACE: str = os.getenv("K8S_NAMESPACE", "default")
GAME_IMAGE: str = os.getenv("GAME_IMAGE", "livetrivia-game:latest")
BEARCAT_API_URL: str = os.getenv("BEARCAT_API_URL", "http://lt-api:8000")
NGINX_POD_LABEL: str = os.getenv("NGINX_POD_LABEL", "app.kubernetes.io/component=nginx")


def _resource_name(game_code: str) -> str:
    """Canonical K8s resource name for a game server."""
    return f"gameserver-{game_code.lower()}"


def _labels(game_code: str) -> dict[str, str]:
    return {
        "managed-by": "livetrivia-api",
        "game-code": game_code,
        "app.kubernetes.io/component": "gameserver",
    }


class K8sGameServerManager:
    """Kubernetes-native game-server lifecycle manager."""

    def __init__(self) -> None:
        self._config_loaded = False

    async def _ensure_config(self) -> None:
        if not self._config_loaded:
            try:
                k8s_config.load_incluster_config()
            except k8s_config.ConfigException:
                await k8s_config.load_kube_config()
            self._config_loaded = True

    async def spawn_game_server(
        self, game_code: str, file_bytes: bytes, game_id: str
    ) -> None:
        await self._ensure_config()

        name = _resource_name(game_code)
        labels = _labels(game_code)

        async with k8s.ApiClient() as api:
            core = k8s.CoreV1Api(api)

            cm = k8s.V1ConfigMap(
                metadata=k8s.V1ObjectMeta(name=name, namespace=K8S_NAMESPACE, labels=labels),
                binary_data={"questions.apkg": base64.b64encode(file_bytes).decode()},
            )
            try:
                await core.create_namespaced_config_map(K8S_NAMESPACE, cm)
            except k8s.ApiException as exc:
                if exc.status == 409:  # already exists
                    await core.replace_namespaced_config_map(name, K8S_NAMESPACE, cm)
                else:
                    raise

            pod = k8s.V1Pod(
                metadata=k8s.V1ObjectMeta(
                    name=name,
                    namespace=K8S_NAMESPACE,
                    labels=labels,
                ),
                spec=k8s.V1PodSpec(
                    restart_policy="Never",
                    containers=[
                        k8s.V1Container(
                            name="game",
                            image=GAME_IMAGE,
                            image_pull_policy="IfNotPresent",
                            ports=[k8s.V1ContainerPort(container_port=3000)],
                            env=[
                                k8s.V1EnvVar(name="BEARCAT_API_URL", value=BEARCAT_API_URL),
                                k8s.V1EnvVar(name="BEARCAT_GAME_ID", value=game_id),
                            ],
                            volume_mounts=[
                                k8s.V1VolumeMount(
                                    name="apkg",
                                    mount_path="/app/questions.apkg",
                                    sub_path="questions.apkg",
                                    read_only=True,
                                ),
                            ],
                        ),
                    ],
                    volumes=[
                        k8s.V1Volume(
                            name="apkg",
                            config_map=k8s.V1ConfigMapVolumeSource(name=name),
                        ),
                    ],
                ),
            )
            try:
                await core.create_namespaced_pod(K8S_NAMESPACE, pod)
            except k8s.ApiException as exc:
                if exc.status == 409:
                    await core.delete_namespaced_pod(name, K8S_NAMESPACE)
                    await core.create_namespaced_pod(K8S_NAMESPACE, pod)
                else:
                    raise

            svc = k8s.V1Service(
                metadata=k8s.V1ObjectMeta(name=name, namespace=K8S_NAMESPACE, labels=labels),
                spec=k8s.V1ServiceSpec(
                    selector=labels,
                    ports=[k8s.V1ServicePort(port=3000, target_port=3000)],
                    type="ClusterIP",
                ),
            )
            try:
                await core.create_namespaced_service(K8S_NAMESPACE, svc)
            except k8s.ApiException as exc:
                if exc.status == 409:
                    await core.delete_namespaced_service(name, K8S_NAMESPACE)
                    await core.create_namespaced_service(K8S_NAMESPACE, svc)
                else:
                    raise

        await self._write_nginx_route(game_code, name)

    async def stop_game_server(self, game_code: str) -> None:
        await self._ensure_config()

        # Remove the nginx route BEFORE deleting the Service so that
        # nginx reload doesn't fail resolving the upstream hostname.
        await self._remove_nginx_route(game_code)

        name = _resource_name(game_code)

        async with k8s.ApiClient() as api:
            core = k8s.CoreV1Api(api)
            for delete_fn, args in (
                (core.delete_namespaced_pod, (name, K8S_NAMESPACE)),
                (core.delete_namespaced_service, (name, K8S_NAMESPACE)),
                (core.delete_namespaced_config_map, (name, K8S_NAMESPACE)),
            ):
                try:
                    await delete_fn(*args)
                except k8s.ApiException as exc:
                    if exc.status != 404:
                        raise

    async def stop_all_game_servers(self) -> None:
        await self._ensure_config()

        label_selector = "managed-by=livetrivia-api"
        async with k8s.ApiClient() as api:
            core = k8s.CoreV1Api(api)

            pods = await core.list_namespaced_pod(
                K8S_NAMESPACE, label_selector=label_selector
            )
            game_codes: list[str] = []
            for pod in pods.items:
                game_codes.append(pod.metadata.labels.get("game-code", ""))

            # Remove nginx routes BEFORE deleting Services so that
            # nginx reload doesn't fail resolving upstream hostnames.
            for code in game_codes:
                if code:
                    await self._remove_nginx_route(code)

            for pod in pods.items:
                try:
                    await core.delete_namespaced_pod(
                        pod.metadata.name, K8S_NAMESPACE
                    )
                except k8s.ApiException:
                    pass

            svcs = await core.list_namespaced_service(
                K8S_NAMESPACE, label_selector=label_selector
            )
            for svc in svcs.items:
                try:
                    await core.delete_namespaced_service(
                        svc.metadata.name, K8S_NAMESPACE
                    )
                except k8s.ApiException:
                    pass

            cms = await core.list_namespaced_config_map(
                K8S_NAMESPACE, label_selector=label_selector
            )
            for cm in cms.items:
                try:
                    await core.delete_namespaced_config_map(
                        cm.metadata.name, K8S_NAMESPACE
                    )
                except k8s.ApiException:
                    pass


    async def _get_nginx_pod_name(self, core: k8s.CoreV1Api) -> str | None:
        pods = await core.list_namespaced_pod(
            K8S_NAMESPACE, label_selector=NGINX_POD_LABEL
        )
        for pod in pods.items:
            if pod.status.phase == "Running":
                return pod.metadata.name
        return None

    async def _nginx_exec(self, command: list[str]) -> None:
        # Use a regular ApiClient for the REST list call, and only
        # WsApiClient for the websocket-based exec call.
        cfg = k8s.Configuration.get_default_copy()
        async with k8s.ApiClient(configuration=cfg) as api:
            core = k8s.CoreV1Api(api)
            pod_name = await self._get_nginx_pod_name(core)
            if pod_name is None:
                logger.warning("nginx pod not found — skipping route update")
                return

        async with WsApiClient(configuration=cfg) as ws_api:
            ws_core = k8s.CoreV1Api(ws_api)
            await ws_core.connect_get_namespaced_pod_exec(
                pod_name,
                K8S_NAMESPACE,
                command=command,
                container="nginx",
                stderr=True,
                stdout=True,
                stdin=False,
                tty=False,
            )

    async def _write_nginx_route(self, game_code: str, service_name: str) -> None:
        # Use a variable + FQDN so nginx resolves DNS at request time (not at
        # reload time) and bypasses /etc/resolv.conf search domains.
        #
        # when proxy_pass uses a variable nginx does not strip the
        # location prefix from the URI.  We use rewrite to strip
        # /gameserver/<CODE>/ so the game server only sees the relative path
        # (e.g. /socket.io/..., /bundle.js, etc.).
        fqdn = f"{service_name}.{K8S_NAMESPACE}.svc.cluster.local"
        conf = (
            f"location /gameserver/{game_code}/ {{\n"
            f"    set $upstream_{game_code.lower()} http://{fqdn}:3000;\n"
            f"    rewrite ^/gameserver/{game_code}/(.*)$ /$1 break;\n"
            f"    proxy_pass $upstream_{game_code.lower()};\n"
            f"    proxy_http_version 1.1;\n"
            f"    proxy_set_header Upgrade $http_upgrade;\n"
            f'    proxy_set_header Connection "upgrade";\n'
            f"    proxy_set_header Host $host;\n"
            f"    proxy_read_timeout 3600;\n"
            f"    proxy_send_timeout 3600;\n"
            f"}}\n"
        )
        path = f"/etc/nginx/conf.d/games/{game_code}.conf"
        await self._nginx_exec(["sh", "-c", f"mkdir -p /etc/nginx/conf.d/games && cat > {path} << 'ENDCONF'\n{conf}ENDCONF"])
        await self._nginx_exec(["nginx", "-s", "reload"])

    async def _remove_nginx_route(self, game_code: str) -> None:
        path = f"/etc/nginx/conf.d/games/{game_code}.conf"
        await self._nginx_exec(["rm", "-f", path])
        await self._nginx_exec(["nginx", "-s", "reload"])
