import unittest

from tests.utils.tools import TestClient, pos_args
from tests.test_client.tools import get_patched_multipackager


class PythonRequiresTest(unittest.TestCase):

    def test_python_requires(self):
        base_conanfile = """from conan import ConanFile
myvar = 123

def myfunct():
    return 234

class Pkg(ConanFile):
    pass
"""

        conanfile = """from conan import ConanFile

class Pkg(ConanFile):
    name = "pyreq"
    version = "1.0.0"
    python_requires = "pyreq_base/0.1@user/channel"

    def build(self):
        v = self.python_requires["pyreq_base"].module.myvar
        f = self.python_requires["pyreq_base"].module.myfunct()
        self.output.info("%s,%s" % (v, f))
"""

        client = TestClient()
        client.save({"conanfile_base.py": base_conanfile})
        client.run(f"export conanfile_base.py { pos_args('pyreq_base/0.1@user/channel') }")

        client.save({"conanfile.py": conanfile})
        mulitpackager = get_patched_multipackager(client, username="user",
                                                          channel="testing",
                                                          exclude_vcvars_precommand=True)
        mulitpackager.add({}, {})
        mulitpackager.run()
        out = mulitpackager.printer.printer.dump()
                
        self.assertIn("pyreq/1.0.0@user/", out)
        self.assertIn(": 123,234", out)
