import os
import unittest
import zipfile

from cpt._compat import environment_append, CONAN_V2
from cpt.test.utils.tools import TestClient, TestServer

from cpt.test.test_client.tools import get_patched_multipackager


class ConfigInstallTest(unittest.TestCase):

    conanfile = """from conan import ConanFile
class Pkg(ConanFile):
    pass
"""

    def test_toolsets_works(self):

        ts = TestServer(users={"user": "password"})
        if CONAN_V2:
            tc = TestClient(servers={"default": ts}, inputs=["user", "password"])
        else:
            tc = TestClient(servers={"default": ts}, users={"default": [("user", "password")]})
        tc.save({"conanfile.py": self.conanfile})

        zip_path = os.path.join(tc.current_folder, 'config.zip')
        zipf = zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED)
        zipf.close()

        with environment_append({"CONAN_UPLOAD": ts.fake_url, "CONAN_LOGIN_USERNAME": "user",
                                 "CONAN_PASSWORD": "password", "CONAN_USERNAME": "user",
                                 "CONAN_CONFIG_URL": zip_path}):
            mulitpackager = get_patched_multipackager(tc, exclude_vcvars_precommand=True)
            mulitpackager.add_common_builds(reference="lib/1.0@user/stable",
                                            shared_option_name=False)
            if CONAN_V2:
                from conan.test.utils.mocks import RedirectedTestOutput
                from conan.test.utils.tools import redirect_output
                output = RedirectedTestOutput()
                with tc.mocked_servers(), redirect_output(output):
                    mulitpackager.run()
                    out = str(output)
            else:
                mulitpackager.run()
                out = str(tc.out)
            self.assertIn("Installing config from address %s" % zip_path, out)
