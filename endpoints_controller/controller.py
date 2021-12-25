import asyncio
import collections

from endpoints_controller.data_struct import Event

import logging

logger = logging.getLogger(__name__)


class EndpointController:

    def __init__(self):
        self.queue = asyncio.Queue()
        self.event_handler = collections.defaultdict(list)
        self.backend = None
        self.locks = {}
        self.lock_lock = asyncio.Lock()

    async def resource_lock(self, event: Event):
        key = (event.kind, event.namespace, event.name)
        if key not in self.locks:
            async with self.lock_lock:
                if key not in self.locks:
                    self.locks[key] = asyncio.Lock()
        return self.locks[key]

    async def new_event(self, event: Event):
        await self.queue.put(event)

    async def run(self):
        while True:
            if self.queue.qsize():
                event = await self.queue.get()
                logger.debug(f'got new event {event}.')
                await self.run_event(event)
                continue
            else:
                # logger.debug(f'no event.')
                await asyncio.sleep(1)

    async def run_event(self, event: Event):
        logger.info(f'run event. {event}')
        async with await self.resource_lock(event):
            for handler in self.event_handler.get((event.kind, event.type)):
                logger.info(f'run event handler {handler}')
                await handler(event)

    def register(self, kind, action):
        def _wrapper(func):
            self.event_handler[(kind, action)].append(func)
            return func

        return _wrapper


controller = EndpointController()
