import unittest

from cpt._compat import CONAN_V2, environment_append
from tests.utils.tools import TestClient, TestServer
from tests.test_client.tools import get_patched_multipackager


class InvalidConfigTest(unittest.TestCase):

    conanfile = """from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
class Pkg(ConanFile):
    name = "lib"
    version = "1.0"
    settings = "arch"

    def configure(self):
        if self.settings.arch == "x86":
            raise ConanInvalidConfiguration("This library doesn't support x86")
"""

    def test_invalid_configuration_skipped_but_warned(self):

        ts = TestServer(users={"user": "password"})
        tc = TestClient(servers={"default": ts}, users={"default": [("user", "password")]})
        tc.save({"conanfile.py": self.conanfile})
        with environment_append({"CONAN_UPLOAD": ts.fake_url, "CONAN_LOGIN_USERNAME": "user",
                                 "CONAN_PASSWORD": "password", "CONAN_USERNAME": "user"}):
            mulitpackager = get_patched_multipackager(tc, exclude_vcvars_precommand=True, gcc_versions=["7"])
            mulitpackager.add({"arch": "x86_64"}, {})
            mulitpackager.add({"arch": "x86"}, {})
            mulitpackager.run()
            out = mulitpackager.printer.printer.dump()

            tmpl = "Uploading package '{0}" if CONAN_V2 else "Uploading packages for '{0}'"
            self.assertIn(tmpl.format("lib/1.0@user/testing"), out)
            self.assertIn("Invalid configuration: This library doesn't support x86", out)
