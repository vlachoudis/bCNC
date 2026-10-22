NAME = bCNC
SOURCES =	bCNC/*.py \
		bCNC/controllers/*.py \
		bCNC/lib/*.py \
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
	rm -f bCNC/plugins/*.pyc bCNC/plugins/*.pyo

upload:
	rm -f dist/*
	#python2 setup.py sdist upload
	python setup.py sdist
	twine upload dist/*
	git tag -f pypi
	git push -f --tags up
