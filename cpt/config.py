import os.path
from conans.model.conf import ConfDefinition
from cpt._compat import CONAN_V2, load, save, get_global_conf, get_evaluated_value


class ConfigManager(object):

    def __init__(self, conan_api, printer):
        self._conan_api = conan_api
        self.printer = printer

    def install(self, url, args=None):
        message = "Installing config from address %s" % url
        if args:
            message += " with args \"%s\"" % args
        self.printer.print_message(message)
        if CONAN_V2:
            self._conan_api.config.install(url, verify_ssl=True,args=args)
        else:
            self._conan_api.config_install(url, verify_ssl=True, args=args)


class GlobalConf(object):
    def __init__(self, conan_api, printer):
        self._conan_api = conan_api
        self.printer = printer

    def populate(self, values):
        global_conf = get_global_conf(self._conan_api)
        if isinstance(values, str):
            values = values.split(",")
        config = ConfDefinition()
        if os.path.exists(global_conf):
            content = load(global_conf)
            config.loads(content)
        for value in values:
            key = value[:value.find('=')]
            k_value = value[value.find('=') + 1:]
            config.update(key, get_evaluated_value(k_value))
        save(global_conf, config.dumps())
