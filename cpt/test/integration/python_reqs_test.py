import unittest

from conans.test.utils.tools import TestClient
from cpt.test.test_client.tools import get_patched_multipackager


class PythonRequiresTest(unittest.TestCase):

    def test_python_requires(self):
        base_conanfile = """from conans import ConanFile
myvar = 123

def myfunct():
    return 234

class Pkg(ConanFile):
    pass
"""

        conanfile = """from conans import ConanFile

class Pkg(ConanFile):
    name = "foo"
    version = "1.0.0"
    python_requires = "pyreq/0.1@user/channel"

    def build(self):
        v = self.python_requires["pyreq"].module.myvar
        f = self.python_requires["pyreq"].module.myfunct()
        self.output.info("%s,%s" % (v, f))
"""

        client = TestClient()
        client.save({"conanfile_base.py": base_conanfile})
        client.run("export conanfile_base.py pyreq/0.1@user/channel")

        client.save({"conanfile.py": conanfile})
        mulitpackager = get_patched_multipackager(client, username="user",
                                                          channel="testing",
                                                          exclude_vcvars_precommand=True)
        mulitpackager.add({}, {})
        mulitpackager.run()
        self.assertIn("Python requires\n    pyreq/0.1@user/channel", client.out)
        self.assertIn("Packages\n    foo/1.0.0@user/testing", client.out)
        self.assertIn("foo/1.0.0@user/testing: 123,234", client.out)
