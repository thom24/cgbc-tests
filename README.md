Congatec Board Controller Tests
===============================

# Prerequisites

* Labgrid setup to access a Congatec board.
* Target shall be running with network and ssh access.
* Target shall have SCP support to deploy the kernel to test.
* Test kernel shall be built with all drivers as built-in, because only the
  kernel is deployed on the target (not the modules).
* Target shall have grub-reboot support with following settings:
  - `menuentry 1` shall boot the kernel to test.
  - kernel to test shall be `/boot/bzImage.test` on the target.

# Usage

Use this command to run test on a Conga-SA7 board.

```shall
pytest tests/ \
	--lg-env targets/conga-sa7.yaml \
	--lg-log \
	--log-cli-level=CONSOLE \
	--lg-colored-steps \
	--kernel-image ../linux/arch/x86_64/boot/bzImage
```

`kernel-image` is optional. If not set, framework will assume the kernel to test
was already deployed and running on the target.
