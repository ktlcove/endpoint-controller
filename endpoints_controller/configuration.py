import os
import typing
import logging

import attr

from ruamel.yaml import YAML

logger = logging.getLogger(__name__)


@attr.s(kw_only=True)
class ReflectHookConfiguration:
    name: str
    type: str
    args = attr.ib(type=typing.List[typing.Any], default=attr.Factory(list))
    kwargs = attr.ib(type=typing.Mapping[str, typing.Any], default=attr.Factory(dict))


@attr.s(kw_only=True)
class Configuration:
    clusterName = attr.ib(type=str, default='default')
    namespaces = attr.ib(type=typing.List[str], default=attr.Factory(lambda: ['.*']))
    namespaceLabelSelector = attr.ib(type=typing.Mapping[str, str], default=attr.Factory(dict))
    serviceLabelSelector = attr.ib(type=typing.Mapping[str, str], default=attr.Factory(dict))
    servicePortNameDefault = attr.ib(type=str, default='http')
    servicePortNameAnnotation = attr.ib(type=str, default='endpointController.portName')
    reflectorHooks = attr.ib(type=typing.List[ReflectHookConfiguration], default=attr.Factory(list))
    ignoreHeadlessService = attr.ib(type=bool, default=True)


def load_configuration() -> Configuration:
    path = os.environ.get('KUBE_ENDPOINT_CONTROLLER_CFG_PATH',
                          '/etc/kube-endpoints-controller/cfg.yaml')

    if os.path.exists(path):
        with open(path) as f:
            _cfg = YAML().load(f)
    else:
        _cfg = {}

    _cfg['reflectorHooks'] = [
        ReflectHookConfiguration(**hook)
        for hook in _cfg.get('reflectorHooks', [])
    ]

    logger.info(_cfg)

    return Configuration(**_cfg)


cfg = load_configuration()
