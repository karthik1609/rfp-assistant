PYINSTALLER ?= pyinstaller

.PHONY: launcher-posix launcher-windows clean-launcher

launcher-posix:
	$(PYINSTALLER) --clean --distpath dist/posix --workpath build/pyinstaller_posix build/launcher_posix.spec

launcher-windows:
	$(PYINSTALLER) --clean --distpath dist/windows --workpath build/pyinstaller_windows build/launcher_windows.spec

clean-launcher:
	rm -rf build/pyinstaller_posix build/pyinstaller_windows dist/posix dist/windows

