import os
import re
import pytest
import yaml

hwmon_temp_labels = [
	"CPU Temperature",
	"Case Temperature",
	"Ambient Temperature",
	"CPU Board Temperature",
	"Carrier Board Temperature",
	"System Chipset Temperature",
	"Video Controller/Board Temperature",
	"Other Temperature",
	"Top DIMM 0 Temperature",
	"Bottom DIMM 0 Temperature",
	"Alternate Board Temperature",
	"Top DIMM 1 Temperature",
	"Top DIMM 2 Temperature",
	"Top DIMM 3 Temperature",
	"Top DIMM 4 Temperature",
	"Top DIMM 5 Temperature",
	"Top DIMM 6 Temperature",
	"Top DIMM 7 Temperature",
	"Bottom DIMM 1 Temperature",
]

# NOTE:
# Channel base is 0 for hwmon_in/hwmon_intrusion, and 1 for everything else:
# in0: "CPU Core Voltage", in1: "DC Runtime Voltage" ...
# temp1: "CPU Temperature", temp2: "Case Temperature" ...
# Can be confusing, but it is handled by the tests.
# Be careful when defining sensors in target yaml file.
hwmon_in_labels = [
	"CPU Core Voltage",
	"DC Runtime Voltage",
	"DC Standby Voltage",
	"CMOS Battery Voltage",
	"Battery Supply Voltage",
	"AC Voltage",
	"Other Voltage",
	"5V Runtime Voltage",
	"5V Standby Voltage",
	"3V3 Runtime Voltage",
	"3V3 Standby Voltage",
	"VCore A Voltage",
	"VCore B Voltage",
	"12V Runtime Voltage",
	"12V Standby Voltage",
]

hwmon_curr_labels = [
	"DC Runtime Current",
	"5V Runtime Current",
	"12V Runtime Current",
]

hwmon_fan_labels = [
	"CPU Fan",
	"Case Fan",
	"Ambient Fan",
	"Chipset Fan",
	"Video Fan",
	"Other Fan",
]


# Valid physical ranges (min, max) for each sensor type. Units match the hwmon
# sysfs attributes:
#   temp_input: millidegrees C
#   in_input:   millivolts
#   curr_input: milliamps
#   fan_input:  RPM
# Voltage sensors (in) have label-specific ranges, indexed 0-based to match
# hwmon_in_labels / the existing channel mapping (in0, in1, ...).
hwmon_range = {
	'temp': (30000, 100000), # 30°C - 100°C
	'curr': (500, 3000),     # 500mA - 3000mA
	'fan': (0, 3000),        # 0RPM - 3000RPM
	'in': {
		1: (4500, 5500),   # DC Runtime Voltage: 4V5 - 5V5
	},
}


def hwmon_get_range(prefix, idx):
	if prefix == 'in':
		return hwmon_range['in'].get(idx, (-1, -1)) # Fallback (-1 -1) so test will fail
	return hwmon_range[prefix]


def hwmon_read_input(ssh, hwmon_path, prefix, idx):
	stdout = ssh.run_check(f"cat {hwmon_path}/{prefix}{idx}_input")
	return int("".join(stdout).strip())


def hwmon_load_hwmon_config(config_path):
	if not config_path or not os.path.exists(config_path):
		return {}
	with open(config_path) as f:
		data = yaml.safe_load(f)
		return data.get('targets', {}).get('main', {}).get('hwmon', {}) or {}


@pytest.fixture(scope="session")
def hwmon_config(request):
	config_path = request.config.option.lg_env or os.environ.get('LG_ENV')
	hwmon = hwmon_load_hwmon_config(config_path)
	_temp = hwmon.get('temp') if 'temp' in hwmon else list(range(1, len(hwmon_temp_labels) + 1))
	_in = hwmon.get('in') if 'in' in hwmon else list(range(0, len(hwmon_in_labels)))
	_curr = hwmon.get('curr') if 'curr' in hwmon else list(range(1, len(hwmon_curr_labels) + 1))
	_fan = hwmon.get('fan') if 'fan' in hwmon else list(range(1, len(hwmon_fan_labels) + 1))
	return {
		'temp': _temp,
		'in': _in,
		'curr': _curr,
		'fan': _fan,
	}


@pytest.fixture(scope="session")
def hwmon_path(session_target):
	ssh = session_target.get_driver("SSHDriver")
	stdout = ssh.run_check("ls /sys/devices/platform/cgbc/cgbc-hwmon/hwmon/")
	hwmon_dev = "".join(stdout).strip().split()[0]
	return f"/sys/devices/platform/cgbc/cgbc-hwmon/hwmon/{hwmon_dev}"


def hwmon_available_indices(ssh, hwmon_path, prefix):
	stdout = ssh.run_check(f"ls -1 {hwmon_path}/")
	indices = set()
	for line in stdout:
		m = re.match(rf"^{prefix}(\d+)_label$", line.strip())
		if m:
			indices.add(int(m.group(1)))
	return indices


def test_hwmon_device_present(session_target, hwmon_path):
	ssh = session_target.get_driver("SSHDriver")
	stdout = ssh.run_check(f"cat {hwmon_path}/name")
	assert "cgbc" in "".join(stdout), f"hwmon device not found at {hwmon_path}"


@pytest.mark.parametrize("idx,expected", [(i, l) for i, l in enumerate(hwmon_temp_labels, start = 1)], ids = [l.replace(" ", "_") for l in hwmon_temp_labels])
def test_hwmon_temp_label(session_target, hwmon_path, hwmon_config, idx, expected):
	if idx not in hwmon_config['temp']:
		pytest.skip(f"temp{idx} not available on this target")
	ssh = session_target.get_driver("SSHDriver")
	stdout = ssh.run_check(f"cat {hwmon_path}/temp{idx}_label")
	assert expected == "".join(stdout).strip(), f"temp{idx}_label mismatch"


@pytest.mark.parametrize("idx", range(1, len(hwmon_temp_labels) + 1), ids=[l.replace(" ", "_") for l in hwmon_temp_labels])
def test_hwmon_temp_input(session_target, hwmon_path, hwmon_config, idx):
	if idx not in hwmon_config['temp']:
		pytest.skip(f"temp{idx} not available on this target")
	ssh = session_target.get_driver("SSHDriver")
	value = hwmon_read_input(ssh, hwmon_path, "temp", idx)
	lo, hi = hwmon_get_range("temp", idx)
	assert lo <= value <= hi, f"temp{idx}_input value {value} outside valid range [{lo}, {hi}]"


@pytest.mark.parametrize("idx,expected", [(i, l) for i, l in enumerate(hwmon_in_labels, start = 0)], ids=[l.replace(" ", "_") for l in hwmon_in_labels])
def test_hwmon_in_label(session_target, hwmon_path, hwmon_config, idx, expected):
	if idx not in hwmon_config['in']:
		pytest.skip(f"in{idx} not available on this target")
	ssh = session_target.get_driver("SSHDriver")
	stdout = ssh.run_check(f"cat {hwmon_path}/in{idx}_label")
	assert expected == "".join(stdout).strip(), f"in{idx}_label mismatch"


@pytest.mark.parametrize("idx", range(0, len(hwmon_in_labels)), ids=[l.replace(" ", "_") for l in hwmon_in_labels])
def test_hwmon_in_input(session_target, hwmon_path, hwmon_config, idx):
	if idx not in hwmon_config['in']:
		pytest.skip(f"in{idx} not available on this target")
	ssh = session_target.get_driver("SSHDriver")
	value = hwmon_read_input(ssh, hwmon_path, "in", idx)
	lo, hi = hwmon_get_range("in", idx)
	assert lo <= value <= hi, f"in{idx}_input value {value} outside valid range [{lo}, {hi}]"


@pytest.mark.parametrize("idx,expected", [(i, l) for i, l in enumerate(hwmon_curr_labels, start = 1)], ids = [l.replace(" ", "_") for l in hwmon_curr_labels])
def test_hwmon_curr_label(session_target, hwmon_path, hwmon_config, idx, expected):
	if idx not in hwmon_config['curr']:
		pytest.skip(f"curr{idx} not available on this target")
	ssh = session_target.get_driver("SSHDriver")
	stdout = ssh.run_check(f"cat {hwmon_path}/curr{idx}_label")
	assert expected == "".join(stdout).strip(), f"curr{idx}_label mismatch"


@pytest.mark.parametrize("idx", range(1, len(hwmon_curr_labels) + 1), ids = [l.replace(" ", "_") for l in hwmon_curr_labels])
def test_hwmon_curr_input(session_target, hwmon_path, hwmon_config, idx):
	if idx not in hwmon_config['curr']:
		pytest.skip(f"curr{idx} not available on this target")
	ssh = session_target.get_driver("SSHDriver")
	value = hwmon_read_input(ssh, hwmon_path, "curr", idx)
	lo, hi = hwmon_get_range("curr", idx)
	assert lo <= value <= hi, f"curr{idx}_input value {value} outside valid range [{lo}, {hi}]"


@pytest.mark.parametrize("idx,expected", [(i, l) for i, l in enumerate(hwmon_fan_labels, start = 1)], ids = [l.replace(" ", "_") for l in hwmon_fan_labels])
def test_hwmon_fan_label(session_target, hwmon_path, hwmon_config, idx, expected):
	if idx not in hwmon_config['fan']:
		pytest.skip(f"fan{idx} not available on this target")
	ssh = session_target.get_driver("SSHDriver")
	stdout = ssh.run_check(f"cat {hwmon_path}/fan{idx}_label")
	assert expected == "".join(stdout).strip(), f"fan{idx}_label mismatch"


@pytest.mark.parametrize("idx", range(1, len(hwmon_fan_labels) + 1), ids = [l.replace(" ", "_") for l in hwmon_fan_labels])
def test_hwmon_fan_input(session_target, hwmon_path, hwmon_config, idx):
	if idx not in hwmon_config['fan']:
		pytest.skip(f"fan{idx} not available on this target")
	ssh = session_target.get_driver("SSHDriver")
	value = hwmon_read_input(ssh, hwmon_path, "fan", idx)
	lo, hi = hwmon_get_range("fan", idx)
	assert lo <= value <= hi, f"fan{idx}_input value {value} outside valid range [{lo}, {hi}]"


def test_hwmon_only_defined_temp_sensors(session_target, hwmon_path, hwmon_config):
	ssh = session_target.get_driver("SSHDriver")
	available = hwmon_available_indices(ssh, hwmon_path, "temp")
	assert available == set(hwmon_config['temp']), \
		f"Available temp sensors {sorted(available)} do not match defined {sorted(hwmon_config['temp'])}"


def test_hwmon_only_defined_in_sensors(session_target, hwmon_path, hwmon_config):
	ssh = session_target.get_driver("SSHDriver")
	available = hwmon_available_indices(ssh, hwmon_path, "in")
	assert available == set(hwmon_config['in']), \
		f"Available in sensors {sorted(available)} do not match defined {sorted(hwmon_config['in'])}"


def test_hwmon_only_defined_curr_sensors(session_target, hwmon_path, hwmon_config):
	ssh = session_target.get_driver("SSHDriver")
	available = hwmon_available_indices(ssh, hwmon_path, "curr")
	assert available == set(hwmon_config['curr']), \
		f"Available curr sensors {sorted(available)} do not match defined {sorted(hwmon_config['curr'])}"


def test_hwmon_only_defined_fan_sensors(session_target, hwmon_path, hwmon_config):
	ssh = session_target.get_driver("SSHDriver")
	available = hwmon_available_indices(ssh, hwmon_path, "fan")
	assert available == set(hwmon_config['fan']), \
		f"Available fan sensors {sorted(available)} do not match defined {sorted(hwmon_config['fan'])}"
