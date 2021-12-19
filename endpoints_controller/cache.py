from endpoints_controller.data_struct import Service


class Cache:

    def __init__(self):
        self.data = {}

    def get(self, namespace, name):
        return self.data.get((namespace, name))

    def set(self, service: Service):
        self.data[(service.namespace, service.name)] = service


cache = Cache()
