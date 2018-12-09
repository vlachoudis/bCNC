NAME = bCNC
SOURCES = bCNC/*.py bCNC/controllers/*.py bCNC/lib/*.py bCNC/plugins/*.py
.PHONY = help

help:
	@echo see source

pot: bCNC/${NAME}.pot

bCNC/${NAME}.pot: ${SOURCES}
	xgettext --from-code=UTF-8 --keyword=N_ -d ${NAME} -o $@ $^
	#pygettext.py -k N_ -d ${NAME} -o $@ $^

tags:
	ctags bCNC/*.py bCNC/lib/*.py bCNC/plugins/*.py

clean:
	git clean -Xf
	#rm -f bCNC/${NAME}.pot
	rm -f bCNC/*.pyc bCNC/*.pyo
	rm -f bCNC/lib/*.pyc bCNC/lib/*.pyo
	rm -f bCNC/plugins/*.pyc bCNC/plugins/*.pyo

upload:
	python2 setup.py sdist upload
