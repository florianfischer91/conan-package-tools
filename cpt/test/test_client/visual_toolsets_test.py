import platform
import unittest

from cpt._compat import environment_append
from cpt.test.utils.tools import TestClient, TestServer

from cpt.test.test_client.tools import get_patched_multipackager
from cpt._compat import CONAN_V2


class VisualToolsetsTest(unittest.TestCase):

    conanfile = """from conan import ConanFile
class Pkg(ConanFile):
    name = "lib"
    version = "1.0"
    settings = "os", "compiler"

    def build(self):
        self.output.warning("HALLO")
"""

    def test_toolsets_works(self):

        ts = TestServer(users={"user": "password"})
        tc = TestClient(servers={"default": ts}, users={"default": [("user", "password")]})
        tc.save({"conanfile.py": self.conanfile})
        with environment_append({"CONAN_UPLOAD": ts.fake_url, "CONAN_LOGIN_USERNAME": "user",
                                 "CONAN_PASSWORD": "password", "CONAN_USERNAME": "user",
                                 "CONAN_VISUAL_TOOLSETS": "17=v140;v140_xp,11=v140;v140_xp"}):
            mulitpackager = get_patched_multipackager(tc, exclude_vcvars_precommand=True)
            mulitpackager.add_common_builds(reference="lib/1.0@user/stable",
                                            shared_option_name=False)
            mulitpackager.run()
            out = mulitpackager.printer.printer.dump()

            if platform.system() == "Windows":
                self.assertIn("Uploading package 1/4", out)
                self.assertIn("Uploading package 2/4", out)
                self.assertIn("Uploading package 3/4", out)
                self.assertIn("Uploading package 4/4", out)
                self.assertIn("compiler.toolset=v140", out)
                self.assertIn("compiler.toolset=v140_xp", out)
            else:
                if CONAN_V2:
                    # TODO We are uploading too many packages...
                    self.assertRegex(out, r"Uploading package 'lib/1.0@user/stable#.*:b351051c2c0b8ed4d5b7a820570b965b73ccf698")
                    self.assertRegex(out, r"Uploading package 'lib/1.0@user/stable#.*:8435e2cb57f34f98567355bbe0a78d98f38f272a")
                else: 
                    self.assertIn("Uploading package 1/2", out)
                    self.assertIn("Uploading package 2/2", out)