import os
import tempfile

from cpt._compat import CONAN_V2, load, _load_profile, get_default_profile_path, save, profile_template
from conans.model.version import Version
from cpt import get_client_version


def get_profiles(client_cache, build_config, base_profile_name=None, is_build_profile=False):

    base_profile_text = ""
    if base_profile_name:
        if CONAN_V2:
            # ugly, client_cache is PkgCache, maybe we have to think about to refactor it so that
            # client_cache is CacheAPI object?
            default_profile_path = os.path.join(client_cache.store,"..", "profiles")
            base_profile_path = os.path.join(default_profile_path, base_profile_name)
        else:
            base_profile_path = os.path.join(client_cache.profiles_path, base_profile_name)

        base_profile_text = load(base_profile_path)
    base_profile_name = base_profile_name or "default"

    if is_build_profile:
        profile_text = "include(%s)" % (base_profile_name)
    else:
        tmp = profile_template


        def pairs_lines(items):
            return "\n".join(["%s=%s" % (k, v) for k, v in items])

        settings = pairs_lines(sorted(build_config.settings.items()))
        options = pairs_lines(build_config.options.items())
        env_vars = pairs_lines(build_config.env_vars.items())
        br_lines = ""
        for pattern, build_requires in build_config.build_requires.items():
            br_lines += "\n".join(["%s:%s" % (pattern, br) for br in build_requires])

        if os.getenv("CONAN_BUILD_REQUIRES"):
            brs = os.getenv("CONAN_BUILD_REQUIRES").split(",")
            brs = ['*:%s' % br.strip() if ":" not in br else br for br in brs]
            if br_lines:
                br_lines += "\n"
            br_lines += "\n".join(brs)

        profile_text = tmp % (base_profile_name, settings, options, env_vars, br_lines)

    return profile_text, base_profile_text


def patch_default_base_profile(conan_api, profile_abs_path):
    """If we have a profile including default, but the users default in config is that the default
    is other, we have to change the include"""
    text = load(profile_abs_path)
    if "include(default)" in text:  # User didn't specified a custom profile
        conan_version = get_client_version()
        if conan_version < Version("1.12.0"):
            cache = conan_api._client_cache
        elif conan_version < Version("1.18.0"):
            cache = conan_api._cache
        else:
            if not conan_api.app:
                conan_api.create_app()
            cache = conan_api.app.cache

        default_profile_name = os.path.basename(get_default_profile_path(conan_api))
        if not os.path.exists(get_default_profile_path(conan_api)):
            conan_api.create_profile(default_profile_name, detect=True)

        if default_profile_name != "default":  # User have a different default profile name
            # https://github.com/conan-io/conan-package-tools/issues/121
            text = text.replace("include(default)", "include(%s)" % default_profile_name)
            save(profile_abs_path, text)


def save_profile_to_tmp(profile_text):
    # Save the profile in a tmp file
    tmp = os.path.join(tempfile.mkdtemp(suffix='conan_package_tools_profiles'), "profile")
    abs_profile_path = os.path.abspath(tmp)
    save(abs_profile_path, profile_text)
    return abs_profile_path


def load_profile(profile_abs_path, conan_api, client_cache):
    return _load_profile(profile_abs_path, conan_api, client_cache)

