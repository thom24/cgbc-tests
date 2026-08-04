import pytest

virtual_storage_devices = {
	"secure-data-eeprom": { "read_only": True, "size": 64 },
	"bios-eeprom": { "read_only": False, "size": 32 },
	"bc-eeprom": { "read_only": True,  "size": 32 },
	"user-eeprom": { "read_only": False, "size": 32 },
	"bios-ram": { "read_only": False, "size": 32 },
	"bc-ram": { "read_only": True, "size": 8 },
	"user-ram": { "read_only": False, "size": 16 }
}


@pytest.mark.parametrize("device", virtual_storage_devices)
def test_virtual_storage_present(session_target, device):
	print(device[0])
	ssh = session_target.get_driver("SSHDriver")
	stdout = ssh.run_check(f"ls /sys/bus/i2c/devices/i2c-cgbc-{device}")
	assert "name" in "".join(stdout), f"Virtual storage device {device} not found"
	stdout = ssh.run_check(f"ls /sys/bus/nvmem/devices/cgbc-{device}*")
	assert "nvmem" in "".join(stdout), f"Virtual storage device {device} not found"


@pytest.mark.parametrize("device", virtual_storage_devices)
def test_virtual_storage_permission(session_target, device):
	ssh = session_target.get_driver("SSHDriver")
	stdout = ssh.run_check(f"ls -al /sys/bus/i2c/devices/i2c-cgbc-{device}/eeprom")
	if virtual_storage_devices[device]['read_only']:
		assert "-r--------" in "".join(stdout), f"Virtual storage device {device} is not read-only"
	else:
		assert "-rw-------" in "".join(stdout), f"Virtual storage device {device} is not read-write"


@pytest.mark.parametrize("device", virtual_storage_devices)
def test_virtual_storage_size(session_target, device):
	ssh = session_target.get_driver("SSHDriver")
	device_size(ssh, device, virtual_storage_devices[device]['size'])


@pytest.mark.parametrize("device", virtual_storage_devices)
def test_virtual_storage_size(session_target, device):
	ssh = session_target.get_driver("SSHDriver")
	stdout = ssh.run_check(f"ls -la /sys/bus/i2c/devices/i2c-cgbc-{device}/eeprom")
	device_size = int("".join(stdout).split()[4])
	assert device_size == size, f"Virtual storage {device} has a {virtual_storage_devices[device]['size']} bytes size instead of {size}"


@pytest.mark.parametrize("device", virtual_storage_devices)
def test_virtual_storage_size(session_target, device):
	ssh = session_target.get_driver("SSHDriver")
	stdout = ssh.run_check(f"dd if=/sys/bus/i2c/devices/i2c-cgbc-{device}/eeprom of=/dev/null bs={virtual_storage_devices[device]['size']} 2>&1")
	assert f"1+0 records in" in "".join(stdout), f"Failed to read device {device}"
	assert f"1+0 records out" in "".join(stdout), f"Failed to read device {device}"


@pytest.mark.parametrize("device", virtual_storage_devices)
def test_virtual_storage_write(session_target, device):
	#### !!! Warning: shall be run only on user-eeprom and user-ram !!!
	if "user" not in device:
		pytest.skip("Write tests are only done on user storage (EEPROM and RAM)")

	size = virtual_storage_devices[device]['size']
	ssh = session_target.get_driver("SSHDriver")
	ssh.run_check(f"dd if=/dev/random of=/tmp/{device}.random bs={size} count=1")
	ssh.run_check(f"dd if=/tmp/{device}.random of=/sys/bus/i2c/devices/i2c-cgbc-{device}/eeprom bs={size} count=1")
	ssh.run_check(f"dd if=/sys/bus/i2c/devices/i2c-cgbc-{device}/eeprom of=/tmp/{device}.read bs={size} count=1")
	# just to get some details in case of debug
	random = ssh.run_check(f"xxd /tmp/{device}.random")
	read = ssh.run_check(f"xxd /tmp/{device}.read")
	sha_random = "".join(ssh.run_check(f"sha256sum /tmp/{device}.random")).split()[0]
	sha_read = "".join(ssh.run_check(f"sha256sum /tmp/{device}.read")).split()[0]
	assert sha_read == sha_random, "Read-back data don't match written data"
