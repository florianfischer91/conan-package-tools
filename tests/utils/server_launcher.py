from conan import conan_version
CONAN_V2 = conan_version.major == 2

if CONAN_V2:
    from conan.test.utils.server_launcher import TestServerLauncher, TESTING_REMOTE_PRIVATE_PASS, TESTING_REMOTE_PRIVATE_USER
else:
    from cpt.test.utils.server_launcher_v1 import TestServerLauncher, TESTING_REMOTE_PRIVATE_USER, TESTING_REMOTE_PRIVATE_PASS