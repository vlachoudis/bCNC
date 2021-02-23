NAME = bCNC
SOURCES =	bCNC/*.py \
		bCNC/controllers/*.py \
		bCNC/lib/*.py \
		bCNC/lib/python_utils/*.py \
		bCNC/lib/stl/*.py \
		bCNC/lib/svg/*.py \
		bCNC/lib/svg/path/*.py \
		bCNC/plugins/*.py
.PHONY = help

help:
	@echo see source

pot: bCNC/${NAME}.pot

bCNC/${NAME}.pot: ${SOURCES}
	xgettext --from-code=UTF-8 --keyword=N_ -d ${NAME} -o $@ $^

tags:
	ctags bCNC/*.py bCNC/lib/*.py bCNC/plugins/*.py

clean:
	git clean -Xf
	rm -f bCNC/*.pyc bCNC/*.pyo
	rm -f bCNC/controllers/*.pyc bCNC/controllers/*.pyo
	rm -f bCNC/lib/*.pyc bCNC/lib/*.pyo
	rm -f bCNC/lib/python_utils/*.pyc bCNC/lib/python_utils/*.pyo
	rm -f bCNC/lib/stl/*.pyc bCNC/lib/stl/*.pyo
	rm -f bCNC/lib/svg/*.pyc bCNC/lib/svg/*.pyo
	rm -f bCNC/lib/svg/path/*.pyc bCNC/lib/svg/path/*.pyo
	rm -f bCNC/plugins/*.pyc bCNC/plugins/*.pyo

upload:
	rm -f dist/*
	#python2 setup.py sdist upload
	python2 setup.py sdist
	twine upload -u $(USER) dist/*
	git tag -f pypi
	git push -f --tags up
