from  cpt._compat import CONAN_V2

if CONAN_V2:
    from conan.test.utils.tools import TestClient, TestServer, RedirectedTestOutput as TestBufferConanOutput
else:
    from cpt.test.utils.tools_v1 import TestClient, TestServer, TestBufferConanOutput