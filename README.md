# pybuilder-docker
A pybuilder plugin that stages a python package into a docker container and optionally publishes it to a registry.

To have pybuilder build a docker image containing the project's package, add `use_plugin("pypi:pybuilder_docker")` to your build.py file, add a Dockerfile and required resources to the folder `src/main/docker`.

Running `pyb docker_package` will build the docker image, `pyb docker_push` will push it to the registry specified via the (mandatory) property `docker_push_registry`.

Note: pybuilder-docker performs a two staged image build, first building a temporary image according to the specified Dockerfile. This image is used as base image to add and install the project artifact in the second stage build. 

### PyBuilder docker properties

Name | Type | Default Value | Description
-- | -- | -- | --
docker_package_build_dir | string | src/main/docker| Directory where (first stage) Dockerfile and it's resources are located
docker_package_build_img | string | $project.name:$project.version| Name of final image
docker_package_build_version| string | $project.version| Version of docker image
docker_package_image_maintainer| string| anonymous| Maintainer information for docker image
docker_package_prepare_env_cmd| string | echo 'empty prepare_env_cmd installing into python'| Command to prepare environment before installation
docker_package_package_cmd| string | pip install $docker_package_dist_file | Installation command
docker_package_dist_file | string | $project.name-$project.version.tar.gz | The project's artifact to add to the container
docker_package_verbose_output|bool| $verbose| TODO: not used yet
docker_push_tag_as_latest|bool|True| Shall docker image be pushed with 'latest' tag as well (in addition to project version)?
docker_push_registry| string | <none>| Mandatory registry to push image to
ensure_ecr_registry_created|bool|True| If repository is an Amazon ECR repo, should registry be created?

### If something went wrong...
In the reports/docker directory, the stdout and stderr output of the various docker commands run by pybuilder-docker are stored. If you encounter any errors during image build or push, check these files for logging info.

### Prerequisites
This plugin requires a locally installed docker client and if the remote container repository is an Amazon ECR locally installed aws tools as well.


