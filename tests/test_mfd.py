def test_mfd_cgbc_version(session_target):
	ssh = session_target.get_driver("SSHDriver")
	stdout = ssh.run_check("cat /sys/devices/platform/cgbc/cgbc_version")
	assert "CGBCP" in "".join(stdout)


def test_mfd_cgbc_unbind_bind(session_target):
	ssh = session_target.get_driver("SSHDriver")
	ssh.run_check("dmesg -c")
	ssh.run_check("echo 'cgbc' > /sys/bus/platform/drivers/cgbc/unbind")
	ssh.run_check("echo 'cgbc' > /sys/bus/platform/drivers/cgbc/bind")
	stdout = "".join(ssh.run_check("dmesg -l emerg,alert,crit,err,warn"))
	assert stdout == "", "Unbinding/binding CGBC MFD driver generated some kernel warning/errors"
