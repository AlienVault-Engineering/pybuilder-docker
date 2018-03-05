import base64
import json
import os
import random
import shutil
import string

from pybuilder.core import Logger, Project, depends, after
from pybuilder.core import task
from pybuilder.pluginhelper.external_command import ExternalCommandBuilder
from pybuilder.utils import assert_can_execute

DOCKER_IMAGE_TEMPLATE = string.Template("""
FROM ${build_image}
MAINTAINER ${maintainer_name}
COPY ${dist_file} .
RUN ${prepare_env_cmd}
RUN ${package_cmd}
""")


@task(description="Package artifact into a docker container.")
@depends("publish")
def docker_package(project, logger):
    # type: (Project, Logger) -> None
    do_docker_package(project, logger)


@after("publish")
def do_docker_package(project, logger):
    project.set_property_if_unset("docker_package_build_dir", "src/main/docker")
    project.set_property_if_unset("docker_package_build_image", project.name)
    project.set_property_if_unset("docker_package_build_version", project.version)
    report_dir = prepare_reports_directory(project)
    dist_dir = prepare_dist_directory(project)
    assert_can_execute(["docker", "--version"], prerequisite="docker", caller="docker_package")
    # is true if user set verbose in build.py or from command line
    verbose = project.get_property("verbose")
    project.set_property_if_unset("docker_package_verbose_output", verbose)
    temp_build_img = 'pyb-temp-{}:{}'.format(project.name, project.version)
    build_img = get_build_img(project)
    logger.info("Executing primary stage docker build for image - {}.".format(build_img))
    # docker build --build-arg buildVersion=${BUILD_NUMBER} -t ${BUILD_IMG} src/
    command = ExternalCommandBuilder('docker', project)
    command.use_argument('build')
    command.use_argument('--build-arg')
    command.use_argument('buildVersion={0}').formatted_with_property('docker_package_build_version')
    command.use_argument('-t')
    command.use_argument('{0}').formatted_with(temp_build_img)
    command.use_argument('{0}').formatted_with_property('docker_package_build_dir')
    command.run("{}/{}".format(report_dir, 'docker_package_build'))
    write_docker_build_file(project=project, logger=logger, build_image=temp_build_img, dist_dir=dist_dir)
    copy_dist_file(project=project, dist_dir=dist_dir, logger=logger)
    logger.info("Executing secondary stage docker build for image - {}.".format(build_img))
    command = ExternalCommandBuilder('docker', project)
    command.use_argument('build')
    command.use_argument('-t')
    command.use_argument('{0}').formatted_with(build_img)
    command.use_argument('{0}').formatted_with(dist_dir)
    command.run("{}/{}".format(report_dir, 'docker_package_img'))
    logger.info("Finished build docker image - {} - with dist file - {}".format(build_img, dist_dir))


def get_build_img(project):
    return project.get_property('docker_package_build_img', '{}:{}'.format(project.name, project.version))


@task(description="Publish artifact into a docker registry.")
@depends("docker_package")
def docker_push(project, logger):
    do_docker_push(project, logger)


def _ecr_login(project, registry):
    command = ExternalCommandBuilder('aws', project)
    command.use_argument('ecr')
    command.use_argument('get-authorization-token')
    command.use_argument('--output')
    command.use_argument('text')
    command.use_argument('--query')
    command.use_argument('authorizationData[].authorizationToken')
    res = command.run("{}/{}".format(prepare_reports_directory(project), 'docker_ecr_get_token'))
    if res.exit_code > 0:
        raise Exception("Error getting token")
    pass_token = base64.b64decode(res.report_lines[0])
    split = pass_token.split(":")
    command = ExternalCommandBuilder('docker', project)
    command.use_argument('login')
    command.use_argument('-u')
    command.use_argument('{0}').formatted_with(split[0])
    command.use_argument('-p')
    command.use_argument('{0}').formatted_with(split[1])
    command.use_argument('{0}').formatted_with(registry)
    res = command.run("{}/{}".format(prepare_reports_directory(project), 'docker_ecr_docker_login'))
    if res.exit_code > 0:
        raise Exception("Error authenticating")
        # aws ecr get-authorization-token --output text --query 'authorizationData[].authorizationToken' | base64 -D | cut -d: -f2
        # docker login -u AWS -p <my_decoded_password> -e <any_email_address> <aws_account_id>.dkr.ecr.us-west-2.amazonaws.com


def _prep_ecr(project, fq_artifact, registry):
    _ecr_login(project, registry)
    create_ecr_registry = project.get_property("ensure_ecr_registry_created", True)
    if create_ecr_registry:
        _create_ecr_registry(fq_artifact, project)


def _create_ecr_registry(fq_artifact, project):
    command = ExternalCommandBuilder('aws', project)
    command.use_argument('ecr')
    command.use_argument('describe-repositories')
    command.use_argument('--repository-names')
    command.use_argument('{0}').formatted_with(fq_artifact)
    res = command.run("{}/{}".format(prepare_reports_directory(project), 'docker_ecr_registry_discover'))
    if res.exit_code > 0:
        command = ExternalCommandBuilder('aws', project)
        command.use_argument('ecr')
        command.use_argument('create-repository')
        command.use_argument('--repository-name')
        command.use_argument('{0}').formatted_with(fq_artifact)
        res = command.run("{}/{}".format(prepare_reports_directory(project), 'docker_ecr_registry_create'))
        if res.exit_code > 0:
            raise Exception("Unable to create ecr registry")


def do_docker_push(project, logger):
    # type: (Project, Logger) -> None
    verbose = project.get_property("verbose")
    project.set_property_if_unset("docker_push_verbose_output", verbose)
    tag_as_latest = project.get_property("docker_push_tag_as_latest", True)
    registry = project.get_mandatory_property("docker_push_registry")
    local_img = get_build_img(project)
    fq_artifact = project.get_property("docker_push_img",get_build_img(project))
    if "ecr" in registry:
        _prep_ecr(project=project, fq_artifact=fq_artifact, registry=registry)
    registry_path =  "{registry}/{fq_artifact}".format(registry=registry, fq_artifact=fq_artifact,)
    tags = [project.version]
    if tag_as_latest: tags.append('latest')
    for tag in tags:
        remote_img = "{registry_path}:{version}".format(registry_path=registry_path,version=tag)
        _run_tag_cmd(project, local_img, remote_img, logger)
        _run_push_cmd(project=project, remote_img=remote_img, logger=logger)
    generate_artifact_manifest(project, registry_path)


def generate_artifact_manifest(project, registry_path):
    artifact_manifest = {'artifact-type': 'container', 'artifact-path': registry_path,
                         'artifact-identifier': project.version}
    with open(project.expand_path('$dir_target', 'artifact.json'), 'w') as target:
        json.dump(artifact_manifest, target)


def _run_tag_cmd(project, local_img, remote_img, logger):
    logger.info("Tagging local docker image {} - {}".format(local_img, remote_img))
    report_dir = prepare_reports_directory(project)
    command = ExternalCommandBuilder('docker', project)
    command.use_argument('tag')
    command.use_argument('{0}').formatted_with(local_img)
    command.use_argument('{0}').formatted_with(remote_img)
    command.run("{}/{}".format(report_dir, 'docker_push_tag'))


def _run_push_cmd(project, remote_img, logger):
    logger.info("Pushing remote docker image - {}".format(remote_img))
    report_dir = prepare_reports_directory(project)
    command = ExternalCommandBuilder('docker', project)
    command.use_argument('push')
    command.use_argument('{0}').formatted_with(remote_img)
    res = command.run("{}/{}".format(report_dir, 'docker_push_tag'))
    if res.exit_code >0:
        logger.info(res.error_report_lines)
        raise Exception("Error pushing image to remote registry - {}".format(remote_img))


#
# docker tag ${APPLICATION}/${ROLE} ${DOCKER_REGISTRY}/${APPLICATION}/${ROLE}:${BUILD_NUMBER}
# docker tag ${DOCKER_REGISTRY}/${APPLICATION}/${ROLE}:${BUILD_NUMBER} ${DOCKER_REGISTRY}/${APPLICATION}/${ROLE}:latest
# docker push ${DOCKER_REGISTRY}/${APPLICATION}/${ROLE}:latest
# docker push ${DOCKER_REGISTRY}/${APPLICATION}/${ROLE}:${BUILD_NUMBER}

def copy_dist_file(project, dist_dir, logger):
    dist_file = get_dist_file(project=project)
    dist_file_path = project.expand_path("$dir_dist", 'dist', dist_file)
    shutil.copy2(dist_file_path, dist_dir)


def write_docker_build_file(project, logger, build_image, dist_dir):
    setup_script = os.path.join(dist_dir, "Dockerfile")
    with open(setup_script, "w") as setup_file:
        setup_file.write(render_docker_buildfile(project, build_image))

    os.chmod(setup_script, 0o755)


def render_docker_buildfile(project, build_image):
    # type: (Project, str) -> str

    dist_file = get_dist_file(project)
    default_package_cmd = "pip install {}".format(dist_file)
    template_values = {
        "build_image": build_image,
        "dist_file": dist_file,
        "maintainer_name": project.get_property("docker_package_image_maintainer",
                                                        "anonymous"),
        "prepare_env_cmd": project.get_property("docker_package_prepare_env_cmd",
                                                "echo 'empty prepare_env_cmd installing into python'"),
        "package_cmd": project.get_property("docker_package_package_cmd", default_package_cmd)
    }

    return DOCKER_IMAGE_TEMPLATE.substitute(template_values)


def get_dist_file(project):
    default_dist_file = "{name}-{version}.tar.gz".format(name=project.name, version=project.version)
    return project.get_property("docker_package_dist_file", default_dist_file)


def randomWord(param):
    return ''.join(random.choice(string.lowercase) for i in range(param))


def prepare_reports_directory(project):
    return prepare_directory("$dir_reports", project)


def prepare_dist_directory(project):
    return prepare_directory("$dir_dist", project)


def prepare_directory(dir_variable, project):
    package__format = "{}/docker".format(dir_variable)
    reports_dir = project.expand_path(package__format)
    if not os.path.exists(reports_dir):
        os.mkdir(reports_dir)
    return reports_dir
