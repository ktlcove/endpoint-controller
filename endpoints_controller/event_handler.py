import logging
import typing

from endpoints_controller.cache import cache
from endpoints_controller.configuration import cfg
from endpoints_controller.controller import controller
from endpoints_controller.data_struct import Service, Endpoint, Event

logger = logging.getLogger(__name__)


async def fetch_svc_from_body(namespace: str, name: str, body: dict) -> typing.Union[Service, None]:
    logger.debug(f'try fetch svc {namespace}.{name} from body: {body}')

    # check service label selector match.
    if cfg.serviceLabelSelector:
        labels = body['metadata'].get('labels', {})  # type: dict
        for k, v in cfg.serviceLabelSelector.items():
            if labels.get(k) != v:
                logger.debug(f'try fetch svc {namespace}.{name} : label mismatch.')
                return
    logger.debug(f'try fetch svc {namespace}.{name} : label matched.')

    # decide service port
    if cfg.servicePortNameLabel:
        labels = body['metadata'].get('labels', {})  # type: dict
        port_name = labels.get(cfg.servicePortNameLabel,
                               cfg.servicePortNameDefault)
    else:
        port_name = cfg.servicePortNameDefault
    logger.debug(f'try fetch svc {namespace}.{name} : port name ({port_name}) decided.')

    svc = Service(
        namespace=namespace,
        name=name,
        port_name=port_name,
    )

    for subset in body.get('subsets', []):
        # available addresses
        if 'addresses' in subset:
            ports = {
                port['name']: port['port']
                for port in subset['ports']
                if port['protocol'] == 'TCP'
            }
            if port_name not in ports:
                logger.error(f'{svc} invalid: {port_name} not found in {ports}.')
                return

            port_number = ports[port_name]
            # port number got, generate endpoints now
            for e in subset['addresses']:
                svc.endpoints.add(Endpoint(ip=e['ip'], port=port_number))

    return svc


@controller.register('endpoints', None)
@controller.register('endpoints', 'ADDED')
async def added_endpoints(event: Event):
    logger.debug(f'run add endpoints handler.')
    svc = await fetch_svc_from_body(event.namespace, event.name, event.body)
    if not svc:
        return
    logger.info(f'{svc} added.')
    await cache.set(svc, action=event.type)


@controller.register('endpoints', 'MODIFIED')
async def modified_svc(event: Event):
    current_svc = cache.get(event.namespace, event.name)
    if not current_svc:
        logger.debug(f'svc {event.namespace}.{event.name} without our label modified.')
        return

    new_svc = await fetch_svc_from_body(event.namespace, event.name, event.body)
    if not new_svc:
        logger.info(f'svc {new_svc} unmarked.')
        await cache.rm(current_svc)
        return

    if new_svc == current_svc:
        logger.info(f'{current_svc} modified but nothing will be change.')
        return

    logger.info(f'{current_svc} changed -> {new_svc}')
    await cache.set(new_svc, action=event.type)


@controller.register('endpoints', 'DELETED')
async def deleted_svc(event: Event):
    current_svc = cache.get(event.namespace, event.name)
    if not current_svc:
        logger.debug(f'svc {event.namespace}.{event.name} without our label deleted.')
        return

    logger.info(f'{current_svc} modified will trigger deleted.')
    await cache.rm(current_svc)
