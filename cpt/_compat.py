from conan import conan_version
import os
from contextlib import contextmanager
from typing import TYPE_CHECKING

CONAN_V2 = conan_version.major == 2

# with conan2 we have to use a pattern for options in the profile
# conan1: gtest:shared=True -> conan2: gtest/*:shared=True
use_pattern = False

if TYPE_CHECKING:
    from cpt.runner import CreateRunner


if CONAN_V2:
    from conan.internal.api.profile import profile_loader
    from conan.internal.api.uploader import UPLOAD_POLICY_FORCE
    from conan.api.conan_api import ConanAPI
    from conans.util.runners import conan_run
    from conan.tools.files import load as _load, save as _save
    from conans.model.recipe_ref import RecipeReference
    from conans.util.files import chdir
    import tempfile
    from conan.tools.scm import Version
    from collections import namedtuple
    from conan.errors import ConanInvalidConfiguration
    from conans.model.conf import ConfDefinition
    
    from contextlib import contextmanager

    use_pattern = True
    
    class ProfileData(namedtuple("ProfileData", ["profiles", "settings", "options", "env", "conf"])):
        def __bool__(self):
            return bool(self.profiles or self.settings or self.options or self.env or self.conf)
        __nonzero__ = __bool__
    
    @contextmanager
    def environment_append(env_vars):
        old_env = dict(os.environ)
        sets = {k: v for k, v in env_vars.items() if v is not None}
        unsets = [k for k, v in env_vars.items() if v is None]
        os.environ.update(sets)
        for var in unsets:
            os.environ.pop(var, None)
        try:
            yield
        finally:
            os.environ.clear()
            os.environ.update(old_env)



    class ConanFileReference(RecipeReference):

        def __iter__(self):
            return iter((self.name, self.version, self.user, self.channel, self.timestamp))
        
        
        @staticmethod
        def loads(rref):
            ret = RecipeReference.loads(rref)
            return ConanFileReference(ret.name, ret.version, ret.user, ret.channel, ret.revision, ret.timestamp)

    class ConanRunner(object):
        def __call__(self, command):
            conan_run(command)

    def load(path):
        return _load(None, path)
    
    def save(path, content):
        return _save(None, path, content)
      
    class Conan(ConanAPI):
        @classmethod
        def factory(cls):
            return cls(), None, None
        
        def create_app(self):
            pass

        @property
        def app(self):
            return self
        
        @property
        def loader(self):
            return self
        
        def load_named(self, path, a1, a2, a3, a4):
            from conan.internal.conan_app import ConanApp
            app = ConanApp(ConanAPI(self.cache_folder))
            return app.loader.load_named(path, a1, a2, a3, a4)
        
        def create(self, conanfile_path, version, profile_build, build_modes):
            from conan.cli.cli import Cli
            cli = Cli(self)
            cli.add_commands()
            print(cli.run(["create", conanfile_path, "--version", version, "--build", build_modes[0] + "/" + version,
                            "--profile:build", profile_build.profiles[0],
                            "--profile:host", profile_build.profiles[0] ]))
            
            

    def _load_profile(profile_abs_path, conan_api, client_cache):
        cache = ConanAPI(conan_api.cache_folder)
        loader = profile_loader.ProfileLoader(conan_api.cache_folder)
        return loader.load_profile("default", profile_abs_path)
    
    profile_template = """
include(%s)

[settings]
%s
[options]
%s
[buildenv]
%s
[tool_requires]
%s
"""

    @contextmanager
    def no_op():
        yield

    def is_windows():
        import platform
        return platform.system() == "Windows"

    def which(cmd):
        from shutil import which
        return which(cmd)
    
    @contextmanager
    def vcvars(*args, **kwargs):
        if is_windows():
            new_env = vcvars_dict(*args, **kwargs)
            with environment_append(new_env):
                yield
        else:
            yield

    def mkdir_tmp():
        return tempfile.mkdtemp(suffix='tmp_conan')
    
    class IterableToFileAdapter(object):
        def __init__(self, iterable, total_size):
            self.iterator = iter(iterable)
            self.total_size = total_size

        def read(self, size=-1):  # @UnusedVariable
            return next(self.iterator, b'')

        def __len__(self):
            return self.total_size

        def __iter__(self):
            return self.iterator.__iter__()
        
    def get_evaluated_value(value):
        # in conan1 it was possible to somehow compose values of different types (f.e. 'True' and true )
        # when composing existing global.conf and new settings
        # in conan2 this compatibility was removed so we need to evaluate
        return  ConfDefinition._get_evaluated_value(value)

else:
    from conans.tools import environment_append, which, no_op, os_info
    from conans.client.conan_api import Conan
    from conans.client.runner import ConanRunner
    
    from conans.client.conan_api import ProfileData
    from conans.model.ref import ConanFileReference
    from conans.client.tools import save, load, chdir, vcvars
    from conans.util.files import mkdir_tmp
    from conans.client.rest.file_uploader import IterableToFileAdapter
    from conans.model.version import Version
    from conans.client import profile_loader
    from conans.client.cmd.uploader import UPLOAD_POLICY_FORCE
    from conans.errors import ConanInvalidConfiguration

    def get_evaluated_value(value):
        return  value

    def _load_profile(profile_abs_path, conan_api, client_cache):
        text = load(profile_abs_path)
        profile, _= profile_loader._load_profile(text, os.path.dirname(profile_abs_path),
                               client_cache.profiles_path)
        return profile
    
    def is_windows():
        return os_info.is_windows
    
    profile_template = """
include(%s)

[settings]
%s
[options]
%s
[env]
%s
[build_requires]
%s
"""


def load_remotes(conan_api):
    if CONAN_V2:
        return conan_api.remotes.list()
    else:
        return conan_api.app.cache.registry.load_remotes()

def get_default_profile_path(conan_api):
    if CONAN_V2:
        return conan_api.profiles.get_default_host()
    else:
        return conan_api.app.cache.default_profile_path
    
def get_global_conf(conan_api):
    if CONAN_V2:
        from conan.api.subapi.config import HomePaths
        ConanAPI(None).config.global_conf
        cache_folder = conan_api.cache_folder

        home_paths = HomePaths(cache_folder)
        global_conf_path = home_paths.global_conf_path
        return global_conf_path
    else:
        return conan_api.app.cache.new_config_path
    
def create_package(self: 'CreateRunner', name, version, channel, user, profile_build):
    if CONAN_V2:
        from conan.cli.commands.create import create
        from argparse import ArgumentParser

        print(self._profile_abs_path)
        print(profile_build)
        cmd = [
            self._conanfile, "--version", str(version), "--name", name,
            "--user", user, "--channel", channel,
            "-l", self._lockfile,
            "-tf", self._test_folder,
            "-pr", self._profile_abs_path
        ]
        
        if self._update_dependencies:
            cmd.append("-u")
        if self._build_policy:
            cmd.extend([f"-b {b}" for b in self._build_policy])

        self._results = create.method(self._conan_api, ArgumentParser(), cmd)["graph"].serialize()
    else:
        self._results = self._conan_api.create(self._conanfile, name=name, version=version,
                                user=user, channel=channel,
                                build_modes=self._build_policy,
                                require_overrides=self._require_overrides,
                                profile_names=[self._profile_abs_path],
                                test_folder=self._test_folder,
                                not_export=self.skip_recipe_export,
                                update=self._update_dependencies,
                                lockfile=self._lockfile,
                                profile_build=profile_build)

def upload_package(self: 'CreateRunner', client_version: Version):
    if CONAN_V2:
        for installed in list(self._results["nodes"].values())[1:]:
            reference = str(ConanFileReference.loads(installed["ref"]))
            if ((reference == str(self._reference)) or
            (reference in self._upload_dependencies) or
            ("all" in self._upload_dependencies)):
                package_id = installed['package_id']
                if installed["binary"] == "Build":
                    if "@" not in reference:
                        reference += "@"
                    if self._upload_only_recipe:
                        self._uploader.upload_recipe(reference, self._upload)
                    else:
                        self._uploader.upload_packages(reference,
                                                    self._upload, package_id)
                else:
                    self.printer.print_message("Skipping upload for %s, "
                                            "it hasn't been built" % package_id)
    else:
        for installed in self._results['installed']:
            reference = installed["recipe"]["id"]
            if client_version >= Version("1.10.0"):
                reference = ConanFileReference.loads(reference)
                reference = str(reference.copy_clear_rev())
            if ((reference == str(self._reference)) or
            (reference in self._upload_dependencies) or
            ("all" in self._upload_dependencies)) and \
            installed['packages']:
                package_id = installed['packages'][0]['id']
                if installed['packages'][0]["built"]:
                    if "@" not in reference:
                        reference += "@"
                    if self._upload_only_recipe:
                        self._uploader.upload_recipe(reference, self._upload)
                    else:
                        self._uploader.upload_packages(reference,
                                                    self._upload, package_id)
                else:
                    self.printer.print_message("Skipping upload for %s, "
                                            "it hasn't been built" % package_id)