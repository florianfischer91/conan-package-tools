
from cpt._compat import CONAN_V2, UPLOAD_POLICY_FORCE

class Uploader(object):

    def __init__(self, conan_api, remote_manager, auth_manager, printer, upload_retry, force):
        self.conan_api = conan_api
        self.remote_manager = remote_manager
        self.auth_manager = auth_manager
        self.printer = printer
        self._upload_retry = upload_retry
        self._force = force
        if not self._upload_retry:
            self._upload_retry = 0

    def upload_recipe(self, reference, upload):
        self._upload_artifacts(reference, upload)

    def upload_packages(self, reference, upload, package_id):
        self._upload_artifacts(reference, upload, package_id)

    def _upload_artifacts(self, reference, upload, package_id=None):
        remote_name = self.remote_manager.upload_remote_name
        if not remote_name:
            self.printer.print_message("Upload skipped, not upload remote available")
            return
        if not self.auth_manager.credentials_ready(remote_name):
            self.printer.print_message("Upload skipped, credentials for remote '%s' not available" % remote_name)
            return

        if upload:

            self.printer.print_message("Uploading packages for '%s'" % str(reference))
            self.auth_manager.login(remote_name)

            
            if CONAN_V2:
                all_packages = package_id is not None
                remote = self.conan_api.remotes.get(remote_name)
                from conan.api.model import ListPattern

                ref_pattern = ListPattern(reference, package_id=package_id or "*", only_recipe= not all_packages)
                package_list = self.conan_api.list.select(ref_pattern)
                self.conan_api.upload.upload_full(package_list,remote=remote,force=self._force, enabled_remotes=self.conan_api.remotes.list())

            else:
                all_packages = package_id is not None
                policy = UPLOAD_POLICY_FORCE if self._force else None
                self.conan_api.upload(str(reference),
                                      all_packages=all_packages,
                                      remote_name=remote_name,
                                      policy=policy,
                                      retry=int(self._upload_retry))
