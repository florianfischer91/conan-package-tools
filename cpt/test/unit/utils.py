import os
from collections import namedtuple

import mock

from cpt._compat import ConanFileReference, replace_in_file, CONAN_V2, Conan
from cpt.test.utils.test_files import temp_folder
from conans.util.files import save
from conans.model.version import Version
from cpt import get_client_version


class MockRunner(object):

    def __init__(self):
        self.reset()
        self.output = ""

    def reset(self):
        self.calls = []

    def __call__(self, command):
        self.calls.append(command)
        return 0


class MockConanCache(object):

    def __init__(self, *args, **kwargs):
        _base_dir = temp_folder()
        self.default_profile_path = os.path.join(_base_dir, "profiles", "default")
        self.profiles_path = os.path.join(_base_dir, "profiles")
        self.new_config_path = os.path.join(_base_dir, "global.conf")
        if not os.path.exists(self.profiles_path):
            os.mkdir(self.profiles_path)

Action = namedtuple("Action", "name args kwargs")

class MockConanAPI(object):

    def __init__(self):
        self.calls = []
        self._client_cache = self._cache = MockConanCache()
        self.app = mock.Mock()
        self.app.cache = self._client_cache
        if CONAN_V2:
            from conan.api.model import PackagesList, ListPattern
            self.config = mock.Mock()
            self.api = Conan(os.path.join(self._client_cache.profiles_path, ".."))
            self.config.config_install = self.config_install
            # there are tests where 'get_path' is called multiple times. For each 'CreateRunner.run' the method is called twice
            # to have always the same behavior we alternate the return value
            does_not_exist = False
            def side_effect(*args, **kwargs):
                nonlocal does_not_exist
                does_not_exist = not does_not_exist
                return  "/random/path/default" if does_not_exist else self.api.profiles.get_path("default", os.getcwd(), exists=False)
            self.profiles = mock.Mock()
            self.profiles.get_path.side_effect = side_effect
            self.cache_folder = self.api.home_folder
            self.remotes = mock.Mock()
            self.remotes.list = self.remote_list
            self.remotes.add = self.remote_add
            self.remotes.user_login = self.authenticate
            def f(l_pattern: ListPattern):
                pkg = PackagesList()
                pkg.add_refs([ConanFileReference.loads(l_pattern.ref)])
            self.list = mock.Mock()
            self.list.select.side_effect = f
            original_upload = self.upload
            self.upload = mock.Mock()
            self.upload.upload_full = original_upload


    def create(self, *args, **kwargs):
        if CONAN_V2:
            d = cmd_to_dict(kwargs["cmd"])
            reference = ConanFileReference(d["--name"], d["--version"], d["--user"], d["--channel"])
            self.calls.append(Action("create", args, kwargs))

            class FakeGraph:
                def serialize(self):
                    return {
                        "nodes": {
                            "cli": "dummy",
                            "node1": {
                                "ref": str(reference),
                                "package_id": "227fb0ea22f4797212e72ba94ea89c7b3fbc2a0c",
                                "binary": "Build",
                            },
                        }
                    }
            return {"graph": FakeGraph()}
        else:
            reference = ConanFileReference(
                kwargs["name"], kwargs["version"], kwargs["user"], kwargs["channel"]
            )
            self.calls.append(Action("create", args, kwargs))
            return {
                "installed": [
                    {
                        "packages": [
                            {
                                "id": "227fb0ea22f4797212e72ba94ea89c7b3fbc2a0c",
                                "built": True,
                            }
                        ],
                        "recipe": {"id": str(reference)},
                    }
                ]
            }

    def create_profile(self, *args, **kwargs):
        save(os.path.join(self._client_cache.profiles_path, args[0]), "[settings]")
        self.calls.append(Action("create_profile", args, kwargs))

    def config_install(self, *args, **kwargs):
        self.calls.append(Action("config_install", args, kwargs))

    def remote_list(self, *args, **kwargs):
        self.calls.append(Action("remote_list", args, kwargs))
        return []

    def remote_add(self, *args, **kwargs):
        self.calls.append(Action("remote_add", args, kwargs))
        return args[0]

    def authenticate(self, *args, **kwargs):
        self.calls.append(Action("authenticate", args, kwargs))

    def upload(self, *args, **kwargs):
        self.calls.append(Action("upload", args, kwargs))

    def get_profile_from_call_index(self, number):
        call = self.calls[number]
        return self.get_profile_from_call(call)

    def get_profile_from_call(self, call):
        if call.name != "create":
            raise Exception("Invalid test, not contains a create: %s" % self.calls)
        conan_version = get_client_version()
        if Version(conan_version) < Version("1.12.0"):
            profile_name = call.kwargs["profile_name"]
        else:
            if CONAN_V2:
                profile_name = call.kwargs["cmd"][call.kwargs["cmd"].index("-pr:h")+1]
            else:
                profile_name = call.kwargs["profile_names"][0]
        replace_in_file(profile_name, "include", "#include")
        if CONAN_V2:
            return self.api.profiles.get_profile([profile_name])
        else:
            from conans.client.profile_loader import read_profile
            return read_profile(profile_name, os.path.dirname(profile_name), None)[0]

    def reset(self):
        self.calls = []

    def get_creates(self):
        return [call for call in self.calls if call.name == "create"]

    def assert_tests_for(self, indexes):
        creates = self.get_creates()
        for create_index, index in enumerate(indexes):
            profile = self.get_profile_from_call(creates[create_index])
            assert("option%s" % index in profile.options)

def cmd_to_dict(cmd):
    d = {}
    for i in range(1, len(cmd[1:]),2):
        if cmd[i] in d and not isinstance(d[cmd[i]], list):
            d[cmd[i]] = [d[cmd[i]], cmd[i+1]]
        elif cmd[i] in d:
            d[cmd[i]].append(cmd[i+1])
        else:
            d[cmd[i]] = cmd[i+1]
    return d

class MockCIManager(object):

    def __init__(self, current_branch=None, build_policy=None, skip_builds=False, is_pull_request=False, is_tag=False):
        self._current_branch = current_branch
        self._build_policy = [build_policy] if build_policy != None and not isinstance(build_policy, list) else build_policy
        self._skip_builds = skip_builds
        self._is_pr = is_pull_request
        self._is_tag = is_tag

    def get_commit_build_policy(self):
        return self._build_policy

    def skip_builds(self):
        return self._skip_builds

    def is_pull_request(self):
        return self._is_pr

    def is_tag(self):
        return self._is_tag

    def get_branch(self):
        return self._current_branch
