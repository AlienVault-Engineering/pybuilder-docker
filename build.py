import os

from pybuilder.core import use_plugin, init

use_plugin("python.core")
use_plugin("python.unittest")
use_plugin("python.install_dependencies")
use_plugin("python.flake8")
use_plugin("python.coverage")
use_plugin("python.distutils")


name = "pybuilder-docker-too"
default_task = "publish"


@init
def set_properties(project):
    build_number = project.get_property("build_number",os.environ.get('GITHUB_RUN_NUMBER',
                                                                      os.environ.get('TRAVIS_BUILD_NUMBER')))

    if build_number is not None and "" != build_number:
        project.version = build_number
    else:
        project.version = "0.0.999"
    #Project Manifest
    project.summary = "A pybuilder plugin that stages a python package into a docker container and optionally publishes it to a registry."
    project.home_page = "https://github.com/rspitler/pybuilder-docker"
    project.description = "A pybuilder plugin that stages a python package into a docker container and optionally publishes it to a registry."
    project.author = "Rspitler"
    project.license = "Apache 2.0"
    project.url = "https://github.com/rspitler/pybuilder-docker"
    # project.depends_on_requirements("requirements.txt")
    #Build and test settings
    project.set_property("run_unit_tests_propagate_stdout",True)
    project.set_property("run_unit_tests_propagate_stderr",True)
    project.set_property("coverage_break_build", False)
    # project.set_property("coverage_branch_threshold_warn", 50)
    # project.set_property("coverage_branch_partial_threshold_warn", 50)
