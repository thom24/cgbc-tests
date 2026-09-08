import os
import pytest
import re
import subprocess
import time
import yaml

from labgrid.protocol import PowerProtocol
from labgrid.protocol import CommandProtocol


def pytest_addoption(parser):
	parser.addoption(
		"--kernel-image",
		metavar="PATH",
		required=False,
		help="path to the kernel image to deploy to /boot/zImage.test, if not set we assume that kernel to test is already running",
	)

def pytest_configure(config):
	if "LG_ENV" not in os.environ and config.option.lg_env:
		os.environ["LG_ENV"] = config.option.lg_env


@pytest.fixture(scope="session")
def session_target(target, request):
	kernel = request.config.getoption("--kernel-image")
#	power = target.get_driver(PowerProtocol)
	ssh = target.get_driver("SSHDriver")

	if kernel is not None:
		kernel = os.path.realpath(kernel)

		result = subprocess.run(["file", kernel], capture_output=True, text=True, check=True)
		m = re.search(r"version\s+(\S+)", result.stdout)
		kernel_version_from_image = m.group(1) if m else None

		ssh.run_check("reboot")
		target.deactivate(ssh)
		target.activate(ssh)

		ssh.put(kernel, "/boot/bzImage.test")
		ssh.run_check("grub-reboot 1")

		ssh.run_check("reboot")
		target.deactivate(ssh)
		target.activate(ssh)

		cmdline = "".join(ssh.run_check("cat /proc/cmdline")).strip()
		if "BOOT_IMAGE=/bzImage.test" not in cmdline:
			raise RuntimeError(f"test kernel not booted: /proc/cmdline={cmdline}")

		uname_r = "".join(ssh.run_check("uname -r")).strip()
		if kernel_version_from_image is not None:
			assert uname_r == kernel_version_from_image, \
				f"Running kernel version '{uname_r}' does not match image version '{kernel_version_from_image}'"

	yield target

	if kernel is not None:
		ssh.run_check("reboot")
		target.deactivate(ssh)
		target.activate(ssh)
