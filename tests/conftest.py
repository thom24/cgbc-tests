import pytest
import time

from labgrid.protocol import PowerProtocol
from labgrid.protocol import CommandProtocol


def pytest_addoption(parser):
	parser.addoption(
		"--kernel-image",
		metavar="PATH",
		required=False,
		help="path to the kernel image to deploy to /boot/zImage.test, if not set we assume that kernel to test is already running",
	)


@pytest.fixture(scope="session")
def session_target(target, request):
	kernel = request.config.getoption("--kernel-image")
#	power = target.get_driver(PowerProtocol)
	ssh = target.get_driver("SSHDriver")

	if kernel is not None:
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

	yield target

	if kernel is not None:
		ssh.run_check("reboot")
		target.deactivate(ssh)
		target.activate(ssh)
