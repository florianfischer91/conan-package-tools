from cpt.packager import ConanMultiPackager
from cpt._compat import Conan, CONAN_V2



def get_patched_multipackager(tc, *args, **kwargs):
    extra_init_kwargs = {}

    if not CONAN_V2:
        extra_init_kwargs.update({'http_requester': tc.requester})


    cache = tc.cache

    if CONAN_V2:
        conan_api = Conan(cache_folder=tc.cache_folder, **extra_init_kwargs)
    else:
        conan_api = Conan(cache_folder=cache.cache_folder, output=tc.out, **extra_init_kwargs)


    if CONAN_V2:
        from conan.test.utils.mocks import RedirectedTestOutput
        class Printer(object):

            def __init__(self, output):
                self.output = output

            def __call__(self, contents):
                self.output.write(contents)

            def dump(self):
                return str(self.output)

        kwargs["out"] = Printer(RedirectedTestOutput())
    else:
        class Printer(object):

            def __init__(self, tc):
                self.tc = tc

            def __call__(self, contents):
                self.tc.out.write(contents)
            
            def dump(self):
                return str(self.tc.out)

        kwargs["out"] = Printer(tc)
    kwargs["conan_api"] = conan_api
    kwargs["cwd"] = tc.current_folder

    mp = ConanMultiPackager(*args, **kwargs)
    if CONAN_V2:
        # in V2, handling the testserver and output works a bit different and we have to use contextmanagers
        # to keep the changes in the tests as little as possible
        from conan.test.utils.tools import redirect_output
        old_run = mp.run
        def _run(*args, **kwargs):
            with tc.mocked_servers(), redirect_output(mp.printer.printer.output):
                old_run(*args, **kwargs)
        mp.run = _run
    return mp
