import asyncio
import collections

from endpoints_controller.data_struct import Event

import logging

logger = logging.getLogger(__name__)


class EndpointController:

    def __init__(self):
        self.queue = asyncio.Queue()
        self.event_handler = collections.defaultdict(list)

    async def new_event(self, event: Event):
        await self.queue.put(event)

    async def run(self):
        while True:
            if self.queue.qsize():
                event = await self.queue.get()  # type: Event
                for handler in self.event_handler.get((event.kind, event.type)):
                    await handler()
            else:
                logger.info('empty queue.')
                await asyncio.sleep(1)

    def register(self, kind, type):
        def _wrapper(func):
            self.event_handler[(kind, type)].append(func)
            return func

        return _wrapper


controller = EndpointController()
