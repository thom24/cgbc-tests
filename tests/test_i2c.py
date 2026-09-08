import os
import pytest
import yaml


def i2c_load_buses(config_path):
	if not config_path or not os.path.exists(config_path):
		return []
	with open(config_path) as f:
		data = yaml.safe_load(f)
		buses = data.get('targets', {}).get('main', {}).get('i2c', {}).get('buses', {}) or {}
		return list(buses.keys())


def i2c_load_devices(config_path):
	if not config_path or not os.path.exists(config_path):
		return {}
	with open(config_path) as f:
		data = yaml.safe_load(f)
		buses = data.get('targets', {}).get('main', {}).get('i2c', {}).get('buses', {}) or {}
		return {
			adapter: [a if isinstance(a, int) else int(a, 16)
				for a in (bus.get('devices', []) or [])]
			for adapter, bus in buses.items()
		}


def pytest_generate_tests(metafunc):
	config_path = metafunc.config.option.lg_env or os.environ.get('LG_ENV')
	if metafunc.function.__name__ == "test_i2c_bus_exists":
		metafunc.parametrize("adapter", i2c_load_buses(config_path),
			ids=lambda s: s.replace(" ", "_"))
	elif metafunc.function.__name__ == "test_i2c_device_visible":
		metafunc.parametrize("adapter", list(i2c_load_devices(config_path)),
			ids=lambda s: s.replace(" ", "_"))


@pytest.fixture(scope="session")
def i2c_config(request):
	config_path = request.config.option.lg_env or os.environ.get('LG_ENV')
	return i2c_load_buses(config_path)


@pytest.fixture(scope="session")
def i2c_devices(request):
	config_path = request.config.option.lg_env or os.environ.get('LG_ENV')
	return i2c_load_devices(config_path)


def test_i2c_bus_exists(session_target, adapter):
	ssh = session_target.get_driver("SSHDriver")
	stdout = "".join(ssh.run_check("i2cdetect -l"))
	assert adapter in stdout, f"I2C bus '{adapter}' not found in i2cdetect -l output"


def test_i2c_bus_no_extra(session_target, i2c_config):
	ssh = session_target.get_driver("SSHDriver")
	lines = ssh.run_check("i2cdetect -l")
	available = { line.split("\t")[2].strip() for line in lines if "cgbc" in line }
	assert available == set(i2c_config), \
		f"Expected Congatec I2C buses {sorted(i2c_config)}, got {sorted(available)}"


def test_i2c_device_visible(session_target, adapter, i2c_devices):
	ssh = session_target.get_driver("SSHDriver")
	expected = set(i2c_devices[adapter])

	bus = None
	for line in ssh.run_check("i2cdetect -l"):
		if adapter in line:
			bus = int(line.split("\t")[0].split("-")[1])
			break
	assert bus is not None, f"Adapter '{adapter}' not found in i2cdetect -l"

	detected = set()
	for line in ssh.run_check(f"i2cdetect -y -r {bus}"):
		cols = line.split()
		if not cols or not cols[0].endswith(":"):
			continue
		row = int(cols[0][:-1], 16)
		for col, cell in enumerate(cols[1:]):
			if cell != "--":
				detected.add(row + col)

	assert detected == expected, \
		f"Bus {bus}: detected {sorted(hex(a) for a in detected)}, " \
		f"expected {sorted(hex(a) for a in expected)}"
