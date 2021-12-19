import logging
import kubernetes

from endpoints_controller.cache import cache
from endpoints_controller.configuration import cfg
from endpoints_controller.controller import controller
from endpoints_controller.data_struct import Service, Endpoint, Event

logger = logging.getLogger(__name__)


async def get_svc_from_kubernetes(namespace, name):
    api = kubernetes.client.CoreV1Api()
    targets = api.list_namespaced_service(namespace=namespace, field_selector=f'metadata.name={name}')
    if targets.items:
        return targets.items[0]
    else:
        return None


async def get_endpoints_from_kubernetes(namespace, name):
    api = kubernetes.client.CoreV1Api()
    targets = api.list_namespaced_endpoints(namespace=namespace, field_selector=f'metadata.name={name}')
    if targets.items:
        return targets.items[0]
    else:
        return None


@controller.event_handler('service', None)
@controller.event_handler('service', 'ADD')
async def resume_svc(event: Event):
    namespace = event.namespace
    name = event.name
    body = event.body
    # a new svc
    # check if headless service
    if cfg.ignoreHeadlessService:
        if not body['spec']['clusterIP']:
            return

    # check service label selector match.
    if cfg.serviceLabelSelector:
        labels = body['metadata'].get('labels', {})  # type: dict
        for k, v in cfg.serviceLabelSelector.items():
            if labels.get(k) != v:
                return

    # decide service port
    if cfg.servicePortNameAnnotation:
        annotations = body['metadata'].get('annotations', {})  # type: dict
        port_name = annotations.get(cfg.servicePortNameAnnotation,
                                    cfg.servicePortNameDefault)
    else:
        port_name = cfg.servicePortNameDefault

    # check port available
    if body['spec'].get('ports'):
        defined_ports = {p['name'] for p in body['spec']['ports']}
        if port_name not in defined_ports:
            logger.warning(f'svc {namespace}.{name}: port {port_name} not defined.')
            return
    else:
        logger.warning(f'svc {namespace}.{name}: empty.')

    logger.info(f'new svc {namespace}.{name}:{port_name}.')

    # if a service created. endpoint must exist when we try to find.
    endpoints_body = await get_endpoints_from_kubernetes(namespace, name)

    # port_number = None
    endpoints = []

    for subset in endpoints_body.get('subsets', []):
        # available addresses
        if subset.haskey('addresses'):
            for port in subset['ports']:
                if port['name'] == port_name and port['protocol'] == 'TCP':
                    port_number = port['port']
                    break
            else:
                logger.error(f'svc {namespace}{name} invalid.')
                return

            # port number got, generate endpoints now
            for e in subset['addresses']:
                endpoints.append(Endpoint(ip=e['ip'], port=port_number))

    cache.set(Service(
        namespace=namespace,
        name=name,
        endpoints=endpoints
    ))
