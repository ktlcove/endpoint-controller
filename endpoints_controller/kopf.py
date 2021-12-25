import asyncio

import kopf

from endpoints_controller.cache import cache
from endpoints_controller.controller import controller
from endpoints_controller.data_struct import Event

from endpoints_controller import event_handler

import logging

logger = logging.getLogger(__name__)


@kopf.on.startup()
async def startup(**_):
    logger.info(f'kopf startup.')
    controller.backend = asyncio.ensure_future(controller.run())
    await cache.init_hooks()


@kopf.on.event("endpoints", when=lambda namespace, **_: namespace != 'kube-system')
async def service_handler(body, name, namespace, type, **_):
    event = Event(
        kind='endpoints',
        type=type,
        namespace=namespace,
        name=name,
        body=body
    )
    # await controller.new_event(event)
    await controller.run_event(event)


# kopf.run(standalone=True, namespaces=cfg.namespaces)
# asyncio.run(kopf.operator(namespaces=cfg.namespaces, standalone=True, ))

def main():


    kopf.run()

    async def _main():
        await kopf.operator(clusterwide=True)
        # namespaces = cfg.namespaces, standalone = True

    loop = asyncio.get_event_loop()
    loop.run
