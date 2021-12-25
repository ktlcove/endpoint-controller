import abc

from endpoints_controller.data_struct import Service


class ABCHook(metaclass=abc.ABCMeta):

    async def init(self):
        pass

    async def trigger(self, action: str, service: Service):
        func = {
            'ADDED': self.on_added,
            'DELETED': self.on_deleted,
            'MODIFIED': self.on_modified,
            None: self.on_recovery,
        }[action]
        return await func(service)  # noqa

    async def on_recovery(self, service: Service):
        pass

    async def on_added(self, service: Service):
        pass

    async def on_modified(self, service: Service):
        pass

    async def on_deleted(self, service: Service):
        pass
