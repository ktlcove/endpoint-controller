import collections
import logging

from endpoints_controller.configuration import cfg
from endpoints_controller.data_struct import Service
from endpoints_controller.hook import HOOKS

logger = logging.getLogger(__name__)


class Cache:

    def __init__(self):
        self.data = {}
        self.hooks = collections.OrderedDict()

    async def init_hooks(self):
        for item in cfg.reflectorHooks:
            assert item.type in HOOKS
            hook = HOOKS[item.type](*item.args, **item.kwargs)
            await hook.init()
            self.hooks[item.name] = hook

    async def trigger_hooks(self, action: str, svc: Service):
        for name, hook in self.hooks.items():
            logger.debug(f'trigger hook {name}:{hook} by {action} {Service}')
            await hook.trigger(action, svc)

    def get(self, namespace, name) -> Service:
        return self.data.get((namespace, name))

    async def set(self, service: Service, *, action: str):
        self.data[(service.namespace, service.name)] = service
        await self.trigger_hooks(action, service)

    async def rm(self, service: Service):
        self.data.pop((service.namespace, service.name))
        await self.trigger_hooks('DELETED', service)


cache = Cache()
