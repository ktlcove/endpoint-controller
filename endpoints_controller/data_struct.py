import attr
import typing


@attr.s
class Event:
    kind = attr.ib(type=str)
    type = attr.ib(type=str)
    namespace = attr.ib(type=str)
    name = attr.ib(type=str)
    body = attr.ib(type=dict, repr=False)


@attr.s
class Endpoint:
    ip = attr.ib(type=str)
    port = attr.ib(type=int)


@attr.s
class Service:
    namespace = attr.ib(type=str)
    name = attr.ib(type=str)
    endpoints = attr.ib(type=typing.List[Endpoint], repr=False, default=attr.Factory(list))
