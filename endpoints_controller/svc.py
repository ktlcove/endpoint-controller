from collections import namedtuple
import os
import kopf
import aiohttp
import asyncio
import json

import kubernetes

from ruamel.yaml import YAML

from kopf._cogs.structs.references import NamespaceName

_cfg_path = os.environ.get('KUBE_ENDPOINT_CONTROLLER_CFG_PATH',
                           '/etc/kube-endpoints-controller/cfg.yaml')
with open(_cfg_path) as f:
    cfg = YAML().load(f)


Endpoint = namedtuple('endpoint', ('ip', 'port'))
Endpoints = namedtuple('endponts', ('name', 'endpoints'))
Event = namedtuple('event', ('type', 'endpoints_group'))


class ABCReflectHook:

    async def trigger(self, event):
        pass


class ApisixReflectHook(ABCReflectHook):

    def __init__(self, *, api_key, admin_url,
                 create_ups=None,
                 create_ups_args=None,
                 default_weight=10,
                 delete_endpoints='mark') -> None:

        self.api_key = api_key
        self.admin_url = admin_url.rstrip('/') + '/'
        self.default_weight = default_weight
        self.create_ups = create_ups if create_ups is not None else True
        self.create_ups_args = create_ups_args or {
            # "id": "1",                  # id
            "retries": 1,               # retry times
            "timeout": {                # Set the timeout for connecting, sending and receiving messages.
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

    async def trigger(self, event: Event):
        print(f'apisix trigger {event}')
        if event.type == 'ADDED':
            if self.create_ups:
                for endpoints in event.endpoints_group:
                    nodes = {f'{n.ip}:{n.port}': self.default_weight
                             for n in endpoints.endpoints}
                    await self.ensure_upstream(name=endpoints.name, nodes=nodes)
        elif event.type == 'MODIFIED' or event.type == None:
            for endpoints in event.endpoints_group:
                nodes = {f'{n.ip}:{n.port}': self.default_weight
                         for n in endpoints.endpoints}
                await self.update_upstream(name=endpoints.name, nodes=nodes)
        elif event.type == 'DELETED':
            for endpoints in event.endpoints_group:
                await self.delete_upstream(name=endpoints.name)
        else:
            raise RuntimeError

    async def _req(self, method, url, **kwargs):
        print(method, f'{self.admin_url}{url}', json.dumps(kwargs))

        async with aiohttp.ClientSession() as session:
            async with session.request(method, f'{self.admin_url}{url}',
                                       headers={'X-API-KEY': self.api_key},
                                       **kwargs) as resp:
                print(f'resp {await resp.text()}')
                return resp.status, await resp.text()

    async def ensure_upstream(self, name, nodes: dict):
        print(f'create upstream {name} {nodes}')
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


class Reflector:

    HOOKS = {
        'apisix': ApisixReflectHook
    }

    def __init__(self) -> None:
        self.hooks = {
            h['name']: self.HOOKS[h['type']](**h['args'])
            for h in cfg['refleatorHooks']
        }

    async def trigger_all(self, event: Event):
        # await asyncio.wait([self.trigger(name, event)
        #                     for name in self.hooks]
        #                    )
        for name in self.hooks:
            await self.trigger(name, event)

    async def trigger(self, name, event: Event):
        hook = self.hooks.get(name)
        await hook.trigger(event)

    def add_hook(self, name, hook):
        self.hooks[name] = hook


reflector = Reflector()


@kopf.on.event("endpoints")
async def sync__changes(body, name, namespace, type, **_):

    # kwargs['type']
    # MODIFIED ADDED DELETED None

    endpoint_ips = [addr['ip']
                    for subset in body.get('subsets', [])
                    for addr in subset.get('addresses', [])]

    event = Event(
        type=type,
        endpoints_group=[
            Endpoints(name=f'{cfg["clusterName"]}.{namespace}.{name}.{port["port"]}',
                      endpoints=[Endpoint(ip=e,
                                          port=port['port'])
                                 for e in endpoint_ips])
            for subset in body.get('subsets', [])
            for port in subset['ports']
        ]
    )

    if type != 'DELETED' and not event.endpoints_group:
        # 如果是删除空 svc 这里缺端口信息
        # 如果是个空 svc endpoints 信息为空 必须从 service 内读到端口信息
        api = kubernetes.client.CoreV1Api()
        services = api.list_namespaced_service(namespace=namespace, field_selector=f'metadata.name={name}')
        ports = services.items[0].spec.ports
        event = Event(
            type=type,
            endpoints_group=[
                Endpoints(name=f'{cfg["clusterName"]}.{namespace}.{name}.{port.target_port}',
                          endpoints=[])
                for port in ports
            ]
        )

    await reflector.trigger_all(event)


@kopf.on.event("service")
async def sync_svc_changes(body, name, namespace, type, **_):

    if type == 'DELETED':
        event = Event(
            type=type,
            endpoints_group=[
                Endpoints(name=f'{cfg["clusterName"]}.{namespace}.{name}.{port["targetPort"]}',
                          endpoints=[])
                for port in body['spec']['ports']
            ]
        )
        await reflector.trigger_all(event)
