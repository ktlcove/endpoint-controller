import json

import aiohttp

from endpoints_controller.data_struct import Service
from endpoints_controller.hook.abc import ABCHook

import logging

logger = logging.getLogger(__name__)


class Apisix(ABCHook):

    def __init__(self, *, cluster_name, api_key, admin_url,
                 create_ups=None,
                 create_ups_args=None,
                 default_weight=10,
                 delete_endpoints='mark') -> None:

        self.cluster_name = cluster_name
        self.api_key = api_key
        self.admin_url = admin_url.rstrip('/') + '/'
        self.default_weight = default_weight
        self.create_ups = create_ups if create_ups is not None else True
        self.create_ups_args = create_ups_args or {
            # "id": "1",                  # id
            "retries": 1,  # retry times
            "timeout": {  # Set the timeout for connecting, sending and receiving messages.
                "connect": 15,
                "send": 15,
                "read": 15,
            },
            # "nodes": {"host:80": 100},  # Upstream machine address list, the format is `Address + Port`
            # is the same as "nodes": [ {"host": "host", "port": 80, "weight": 100} ],
            "type": "roundrobin",
            # "checks": {},               # Health check parameters
            # "hash_on": "",
            # "key": "",
            # "name": "upstream-for-test",
            "desc": "Auto created by KER.",
            # "scheme": "http",           # The scheme used when communicating with upstream, the default is `http`
        }
        self.delete_endpoints = delete_endpoints

    def svc_name(self, service: Service):
        return f'{service.name}.{service.namespace}.{self.cluster_name}'

    def svc_nodes(self, service: Service):
        return {f'{e.ip}:{e.port}': self.default_weight
                for e in service.endpoints}

    async def on_modified(self, service: Service):
        await self.update_upstream(name=self.svc_name(service),
                                   nodes=self.svc_nodes(service))

    async def on_deleted(self, service: Service):
        await self.delete_upstream(name=self.svc_name(service))

    async def on_recovery(self, service: Service):
        await self.on_modified(service)

    async def on_added(self, service: Service):
        if self.create_ups:
            await self.ensure_upstream(name=self.svc_name(service),
                                       nodes=self.svc_nodes(service))

    async def _req(self, method, url, **kwargs):
        logger.debug(f'apisix call {method} {self.admin_url}{url} with {json.dumps(kwargs)}')

        async with aiohttp.ClientSession() as session:
            async with session.request(method, f'{self.admin_url}{url}',
                                       headers={'X-API-KEY': self.api_key},
                                       **kwargs) as resp:
                logger.debug(f'apisix resp {await resp.text()}')
                return resp.status, await resp.text()

    async def ensure_upstream(self, name, nodes: dict):
        logger.info(f'apisix create upstream {name} {nodes}')
        return await self._req('PUT', f'upstreams/{name}',
                               json={
                                   **self.create_ups_args,
                                   'nodes': nodes,
                                   'name': name,
                               })

    async def update_upstream(self, name, nodes: dict):
        code, ups = await self._req('GET', f'upstreams/{name}')
        if code == 404:
            if self.create_ups:
                return await self.ensure_upstream(name, nodes)
        else:
            logger.info(f'apisix update upstream {name} {nodes}')
            return await self._req('PATCH', f'upstreams/{name}/nodes', json=nodes)
            #
            # ! another way to sync , backup here don't clear
            #
            # ups = json.loads(ups)
            # old_nodes = ups.get('nodes', {})
            # expired_nodes = {n: None
            #                  for n in old_nodes if n not in nodes}
            # new_nodes = {n: cfg.apisix.default_weight
            #              for n in nodes if n not in old_nodes}

            # final_nodes = {**expired_nodes,  **new_nodes}
            # print(f'update nodes from ups: {name}, {final_nodes}')
            # await self._req('PATCH', f'upstream/{name}',
            # json={'nodes': final_nodes})

    async def delete_upstream(self, name):
        if self.delete_endpoints == 'delete':
            await self._req('DELETE', f'upstreams/{name}')
        else:
            await self._req('PATCH', f'upstreams/{name}', json={'desc': '# KER WARNING ! to delete !'})
