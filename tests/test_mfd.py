def test_mfd_cgbc_version(session_target):
	ssh = session_target.get_driver("SSHDriver")
	stdout = ssh.run_check("cat /sys/devices/platform/cgbc/cgbc_version")
	assert "CGBCP" in "".join(stdout)

