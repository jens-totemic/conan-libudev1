import os
from conans import ConanFile, AutoToolsBuildEnvironment, tools
from conans.client.tools.oss import get_gnu_triplet

class DebianDependencyConan(ConanFile):
    name = "libudev1"
    version = "229"
    build_version = "4ubuntu21.22" 
    homepage = "https://packages.ubuntu.com/xenial-updates/libudev1"
    # dev_url = https://packages.ubuntu.com/xenial-updates/libudev-dev
    description = "libudev provides APIs to introspect and enumerate devices on the local system"
    url = "https://github.com/jens-totemic/conan-libudev1"    
    license = "LGPL"
    settings = "os", "arch"

    def configure(self):
        if self.settings.os != "Linux":
            raise ConanInvalidConfiguration("This library is only supported on Linux")

    def translate_arch(self):
        arch_string = str(self.settings.arch)
        # ubuntu does not have v7 specific libraries
        if (arch_string) == "armv7hf":
            return "armhf"
        elif (arch_string) == "armv8":
            return "arm64"
        elif (arch_string) == "x86_64":
            return "amd64"
        return arch_string
        
    def _download_extract_deb(self, url, sha256):
        filename = "./download.deb"
        deb_data_file = "data.tar.xz"
        tools.download(url, filename)
        tools.check_sha256(filename, sha256)
        # extract the payload from the debian file
        self.run("ar -x %s %s" % (filename, deb_data_file))
        os.unlink(filename)
        tools.unzip(deb_data_file)
        os.unlink(deb_data_file)

    def triplet_name(self):
        # we only need the autotool class to generate the host variable
        autotools = AutoToolsBuildEnvironment(self)

        # construct path using platform name, e.g. usr/lib/arm-linux-gnueabihf/pkgconfig
        # if not cross-compiling it will be false. In that case, construct the name by hand
        return autotools.host or get_gnu_triplet(str(self.settings.os), str(self.settings.arch), self.settings.get_safe("compiler"))
        
    def build(self):
        if self.settings.os == "Linux":
            if self.settings.arch == "x86_64":
                # https://packages.ubuntu.com/xenial-updates/amd64/libudev1/download
                sha_lib = "f23a5177625f76aadbccc2294b2194aadff62340cdf9c060d87b30026bc06940"
                # https://packages.ubuntu.com/xenial-updates/amd64/libudev-dev/download
                sha_dev = "b1ecd7a654c196c0d7dbedb57605e00fa0141175a0adbc749bf425b3cac1a52a"
                
                url_lib = ("http://us.archive.ubuntu.com/ubuntu/pool/main/s/systemd/libudev1_%s-%s_%s.deb"
                   % (str(self.version), self.build_version, self.translate_arch()))
                url_dev = ("http://us.archive.ubuntu.com/ubuntu/pool/main/s/systemd/libudev-dev_%s-%s_%s.deb"
                   % (str(self.version), self.build_version, self.translate_arch()))
            elif self.settings.arch == "armv8":
                # https://packages.ubuntu.com/xenial-updates/arm64/libudev1/download
                sha_lib = "04278009fdc066b464d89d7793b6bdb10d1197abee79e7c516ca1395a4eca9e6"
                # https://packages.ubuntu.com/xenial-updates/arm64/libudev-dev/download
                sha_dev = "713dddc53cf119c3c8d8072b78c6e158815db7ac287aa4b836fcae9bf8b3d643"
                
                url_lib = ("http://ports.ubuntu.com/ubuntu-ports/pool/main/s/systemd/libudev1_%s-%s_%s.deb"
                   % (str(self.version), self.build_version, self.translate_arch()))
                url_dev = ("http://ports.ubuntu.com/ubuntu-ports/pool/main/s/systemd/libudev-dev_%s-%s_%s.deb"
                   % (str(self.version), self.build_version, self.translate_arch()))
            else: # armv7hf
                # https://packages.ubuntu.com/xenial-updates/armhf/libudev1/download
                sha_lib = "eaed25258fb0a6f5cc1ac016e14a2cd4646a690a0e6599f886174f4a789d5c5d"
                # https://packages.ubuntu.com/xenial-updates/armhf/libudev-dev/download
                sha_dev = "6f85a06df5da97051aa144206ce16292cf6d2c317fab453c8f6fdf4baa7b19f6"
                
                url_lib = ("http://ports.ubuntu.com/ubuntu-ports/pool/main/s/systemd/libudev1_%s-%s_%s.deb"
                   % (str(self.version), self.build_version, self.translate_arch()))
                url_dev = ("http://ports.ubuntu.com/ubuntu-ports/pool/main/s/systemd/libudev-dev_%s-%s_%s.deb"
                   % (str(self.version), self.build_version, self.translate_arch()))
            self._download_extract_deb(url_lib, sha_lib)
            self._download_extract_deb(url_dev, sha_dev)
            # remove libudev.so which is an absolute link to /lib/arm-linux-gnueabihf/libudev.so.1.6.4
            lib_so_path = "usr/lib/%s/libudev.so" % self.triplet_name()
            os.remove(lib_so_path)
            os.symlink("libudev.so.1.6.4", lib_so_path)
        else:
            self.output.info("Nothing to be done for this OS")

    def package(self):
        self.copy(pattern="*", dst="lib", src="lib/" + self.triplet_name(), symlinks=True)
        self.copy(pattern="*", dst="lib", src="usr/lib/" + self.triplet_name(), symlinks=True)
        self.copy(pattern="*", dst="include", src="usr/include", symlinks=True)
        self.copy(pattern="copyright", src="usr/share/doc/" + self.name, symlinks=True)

    def copy_cleaned(self, source, prefix_remove, dest):
        for e in source:
            if (e.startswith(prefix_remove)):
                entry = e[len(prefix_remove):]
                if len(entry) > 0 and not entry in dest:
                    dest.append(entry)

    def package_info(self):
        # pkgpath = "usr/lib/%s/pkgconfig" % self.triplet_name()
        pkgpath =  "lib/pkgconfig"
        pkgconfigpath = os.path.join(self.package_folder, pkgpath)
        if self.settings.os == "Linux":
            self.output.info("package info file: " + pkgconfigpath)
            with tools.environment_append({'PKG_CONFIG_PATH': pkgconfigpath}):
                pkg_config = tools.PkgConfig("libudev", variables={ "prefix" : self.package_folder } )

                self.output.info("lib_paths %s" % self.cpp_info.lib_paths)

                # exclude all libraries from dependencies here, they are separately included
                self.copy_cleaned(pkg_config.libs_only_l, "-l", self.cpp_info.libs)
                self.output.info("libs: %s" % self.cpp_info.libs)

                self.output.info("include_paths: %s" % self.cpp_info.include_paths)
