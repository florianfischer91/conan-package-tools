import unittest

from cpt.config import ConfigManager
from cpt.printer import Printer
from cpt.test.integration.base import BaseTest
from cpt.test.unit.packager_test import MockConanAPI
from cpt._compat import CONAN_V2, ConanException

class RemotesTest(unittest.TestCase):

    def setUp(self):
        self.conan_api = MockConanAPI()

    def test_valid_config(self):
        manager = ConfigManager(self.conan_api, Printer())
        manager.install('https://github.com/bincrafters/bincrafters-config.git')

    def test_valid_config_with_args(self):
        manager = ConfigManager(self.conan_api, Printer())
        manager.install('https://github.com/bincrafters/bincrafters-config.git', '-b main')


class RemotesTestRealApi(BaseTest):

    def test_valid_config(self):
        manager = ConfigManager(self.api, Printer())
        if CONAN_V2:
            profiles = self.api.profiles.list()
        else:
            profiles = self.api.profile_list()
        
        self.assertEquals(len(profiles), 0)

        manager.install("https://github.com/bincrafters/bincrafters-config.git", "-b main")
        if CONAN_V2:
            profiles = self.api.profiles.list()
        else:
            profiles = self.api.profile_list()
        self.assertGreater(len(profiles), 3)

    def test_invalid_config(self):
        manager = ConfigManager(self.api, Printer())

        if CONAN_V2:
            profiles = self.api.profiles.list()
        else:
            profiles = self.api.profile_list()
        self.assertEquals(len(profiles), 0)

        try:
            manager.install("https://github.com/")
            self.fail("Could not accept wrong URL")
        except ConanException:
            pass
