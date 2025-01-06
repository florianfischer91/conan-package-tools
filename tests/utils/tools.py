from  cpt._compat import CONAN_V2

if CONAN_V2:
    from conan.test.utils.tools import TestClient as TestClientV2, TestServer, RedirectedTestOutput as TestBufferConanOutput

    def pos_args(args_str: str):
        ret = ""
        if "@" in args_str:
            name_version, args_str = args_str.split("@")
            ret = "--name={0} --version={1} ".format(*name_version.split("/"))
        return "{0}--user={1} --channel={2}".format(ret, *args_str.split("/"))
    
    class TestClient(TestClientV2):
        def __init__(self, cache_folder=None, current_folder=None, servers=None, users=None, requester_class=None, path_with_spaces=True, default_server_user=None, light=False, custom_commands_folder=None):
            # in v2 inputs is only a list
            inputs = list(list(users.values())[0][0]) if users else users
            super().__init__(cache_folder, current_folder, servers, inputs, requester_class, path_with_spaces, default_server_user, light, custom_commands_folder)
else:
    from cpt.test.utils.tools_v1 import TestClient, TestServer, TestBufferConanOutput

    def pos_args(args_str: str):
        return args_str
        