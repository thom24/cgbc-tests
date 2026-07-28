import pytest


def backlight_get_actual_brightness(ssh):
	stdout = ssh.run_check("cat /sys/class/backlight/cgbc-backlight/actual_brightness")
	return int("".join(stdout).split()[0])


def test_backlight_device_present(session_target):
	ssh = session_target.get_driver("SSHDriver")
	stdout = ssh.run_check("ls /sys/class/backlight/cgbc-backlight/")
	assert "actual_brightness" in "".join(stdout), "Backlight device not found"


def test_backlight_read_max_brightness(session_target):
	ssh = session_target.get_driver("SSHDriver")
	stdout = ssh.run_check("cat /sys/class/backlight/cgbc-backlight/max_brightness")
	assert 100 == int("".join(stdout).split()[0]), "Failed to read max_brightness"


def test_backlight_read_brightness(session_target):
	ssh = session_target.get_driver("SSHDriver")
	assert 100 <= backlight_get_actual_brightness(ssh), "Failed to read brightness"


@pytest.mark.parametrize("brightness", [ 0, 25, 50, 75, 100 ])
def test_backlight_set_brightness(session_target, brightness):
	ssh = session_target.get_driver("SSHDriver")
	ssh.run_check(f"echo {brightness} > /sys/class/backlight/cgbc-backlight/brightness")
	actual_brightness = backlight_get_actual_brightness(ssh)
	assert brightness == actual_brightness, f"Actual brightness ({actual_brightness}) does not match brightness ({brightness})"
