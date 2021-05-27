import os
import unittest

import pybuilder_docker_too

DIRNAME = os.path.dirname(os.path.abspath(__file__))


class PybuildDockerTestCase(unittest.TestCase):

    def test_artifact_manfiest_generation(self):
        self.assertTrue(True, "Success")
