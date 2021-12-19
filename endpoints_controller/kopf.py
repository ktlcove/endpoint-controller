import asyncio

import kopf

from endpoints_controller.configuration import cfg
from endpoints_controller.controller import controller
from endpoints_controller.data_struct import Event


@kopf.on.event("service")
async def service_handler(body, name, namespace, type, **_):
    await controller.new_event(event=Event(
        kind='service',
        type=type,
        namespace=namespace,
        name=name,
        body=body
    ))

# kopf.run(standalone=True, namespaces=cfg.namespaces)
# asyncio.run(kopf.operator(namespaces=cfg.namespaces, standalone=True, ))
