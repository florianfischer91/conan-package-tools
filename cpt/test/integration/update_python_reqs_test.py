import unittest

from cpt._compat import CONAN_V2
from cpt.test.utils.tools import TestClient
from cpt.test.test_client.tools import get_patched_multipackager


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
        if CONAN_V2:
            client.run("export conanfile_base.py --name=pyreq_base --version=0.1 --user=user --channel=channel")
        else:
            client.run("export conanfile_base.py pyreq_base/0.1@user/channel")

        client.save({"conanfile.py": conanfile})
        mulitpackager = get_patched_multipackager(client, username="user",
                                                          channel="testing",
                                                          exclude_vcvars_precommand=True)
        mulitpackager.add({}, {})
        if CONAN_V2:
            from conan.test.utils.mocks import RedirectedTestOutput
            from conan.test.utils.tools import redirect_output
            output = RedirectedTestOutput()
            with redirect_output(output):
                mulitpackager.run()
                output.seek(0)
                out = output.read()
        else:
            mulitpackager.run()
            out = client.out
                
        self.assertIn("pyreq/1.0.0@user/", out)
        self.assertIn(": 123,234", out)
