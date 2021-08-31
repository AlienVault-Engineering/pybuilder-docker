#!/usr/bin/env python
#   -*- coding: utf-8 -*-

from setuptools import setup
from setuptools.command.install import install as _install

class install(_install):
    def pre_install_script(self):
        pass

    def post_install_script(self):
        pass

    def run(self):
        self.pre_install_script()

        _install.run(self)

        self.post_install_script()

if __name__ == '__main__':
    setup(
        name = 'pybuilder-docker',
        version = '0.1.14',
        description = 'A pybuilder plugin that stages a python package into a docker container and optionally publishes it to a registry.',
        long_description = 'A pybuilder plugin that stages a python package into a docker container and optionally publishes it to a registry.',
        long_description_content_type = None,
        classifiers = [
            'Development Status :: 3 - Alpha',
            'Programming Language :: Python'
        ],
        keywords = '',

        author = '',
        author_email = '',
        maintainer = '',
        maintainer_email = '',

        license = 'Apache 2.0',

        url = 'https://github.com/AlienVault-Engineering/pybuilder-docker',
        project_urls = {},

        scripts = [],
        packages = ['pybuilder_docker'],
        namespace_packages = [],
        py_modules = [],
        entry_points = {},
        data_files = [],
        package_data = {},
        install_requires = [],
        dependency_links = [],
        zip_safe = True,
        cmdclass = {'install': install},
        python_requires = '',
        obsoletes = [],
    )
