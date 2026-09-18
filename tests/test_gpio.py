import os
import re
import pytest
import yaml

gpioget_cmd="gpioget --numeric -c"
gpioset_cmd="gpioset -t 0 -c"
gpioinfo_cmd="gpioinfo -c"


def gpio_load_config(config_path):
	if not config_path or not os.path.exists(config_path):
		return {}
	with open(config_path) as f:
		data = yaml.safe_load(f)
		return data.get('targets', {}).get('main', {}).get('gpio', {}) or {}


@pytest.fixture(scope="session")
def gpio_config(request):
	config_path = request.config.option.lg_env or os.environ.get('LG_ENV')
	return gpio_load_config(config_path)


def pytest_generate_tests(metafunc):
	config_path = metafunc.config.option.lg_env or os.environ.get('LG_ENV')
	if metafunc.function.__name__ == "test_gpio_cgbc_loopback":
		loopbacks = gpio_load_config(config_path).get('loopbacks', {}) or {}
		metafunc.parametrize("gpio_a,gpio_b", list(loopbacks.items()),
			ids=[f"gpio{gpio_a}-gpio{gpio_b}" for gpio_a, gpio_b in loopbacks.items()])
	elif metafunc.function.__name__ == "test_gpio_cgbc_valid_mask":
		config = gpio_load_config(config_path)
		lines = config.get('lines')
		assert lines is not None, "gpio lines not defined in target config"
		mask = config.get('valid_mask') or [1] * lines
		metafunc.parametrize("gpio_line,valid", list(enumerate(mask)),
			ids=[f"gpio{line}-{'valid' if valid else 'invalid'}" for line, valid in enumerate(mask)])


def gpioset(ssh, chip, line, value):
	ssh.run_check(f"{gpioset_cmd} {chip} {line}={value}")


def gpioget(ssh, chip, line):
	stdout = ssh.run_check(f"{gpioget_cmd} {chip} {line}")
	return int("".join(stdout).strip())


def gpioinfo(ssh, chip, line):
	return "".join(ssh.run_check(f"{gpioinfo_cmd} {chip} {line}"))


def gpio_cgbc_match(ssh):
	stdout = "".join(ssh.run_check("gpiodetect"))
	m = re.search(r"(gpiochip\d+) \[cgbc-gpio(\.\d+\.auto)?\] \((\d+) lines\)", stdout)
	assert m is not None, f"cgbc-gpio gpiochip not found in gpiodetect output:\n{stdout}"
	return m


def gpio_cgbc_chip_id(ssh):
	return gpio_cgbc_match(ssh).group(1)


def test_gpio_cgbc_gpiochip_present(session_target):
	ssh = session_target.get_driver("SSHDriver")
	gpio_cgbc_match(ssh)


def test_gpio_cgbc_line_count(session_target, gpio_config):
	lines = gpio_config.get('lines')
	assert lines is not None, "gpio lines not defined in target config"
	ssh = session_target.get_driver("SSHDriver")
	m = gpio_cgbc_match(ssh)
	detected = int(m.group(3))
	assert detected == lines, \
		f"cgbc-gpio reports {detected} lines, expected {lines} from target config"


def test_gpio_cgbc_valid_mask(session_target, gpio_line, valid):
	ssh = session_target.get_driver("SSHDriver")
	chip = gpio_cgbc_chip_id(ssh)
	stdout = gpioinfo(ssh, chip, gpio_line)
	if valid:
		assert 'consumer="kernel"' not in stdout, \
			f"gpio line {gpio_line} is expected to be valid (not claimed by kernel):\n{stdout}"
	else:
		assert 'consumer="kernel"' in stdout, \
			f"gpio line {gpio_line} is expected to be invalid (claimed by kernel):\n{stdout}"


def test_gpio_cgbc_loopback(session_target, gpio_a, gpio_b):
	ssh = session_target.get_driver("SSHDriver")
	chip = gpio_cgbc_chip_id(ssh)
	try:
		for a, b in ((gpio_a, gpio_b), (gpio_b, gpio_a)):
			for line in (a, b):
				gpioget(ssh, chip, line)
			for value in (1, 0):
				gpioset(ssh, chip, a, value)
				read = gpioget(ssh, chip, line)
				assert read == value, \
					f"loopback {a} -> {b}: read {read}, expected {value}"
	finally:
		for line in (gpio_a, gpio_b):
			gpioget(ssh, chip, line)
