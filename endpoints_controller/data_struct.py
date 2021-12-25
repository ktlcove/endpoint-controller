import attr
import typing

import logging

logger = logging.getLogger(__name__)


@attr.s
class Event:
    kind = attr.ib(type=str)
    type = attr.ib(type=str)
    namespace = attr.ib(type=str)
    name = attr.ib(type=str)
    body = attr.ib(type=dict, repr=False)

    def __attrs_post_init__(self):
        logger.debug(f'{self} created.')


@attr.s(hash=False)
class Endpoint:
    ip = attr.ib(type=str)
    port = attr.ib(type=int)

    def __hash__(self):
        return hash((self.ip, self.port))


@attr.s(eq=False, hash=False)
class Service:
    namespace = attr.ib(type=str)
    name = attr.ib(type=str)
    port_name = attr.ib(type=str)
    endpoints = attr.ib(type=typing.List[Endpoint], repr=False, default=attr.Factory(set))

    def __eq__(self, other: 'Service'):
        return self.namespace == other.namespace and \
               self.name == other.name and \
               self.port_name == other.port_name \
               and len(self.endpoints) == len(other.endpoints) \
               and all(e in other.endpoints for e in self.endpoints) \
               and all(e in self.endpoints for e in other.endpoints)
