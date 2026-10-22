NAME = bCNC
POT = bCNC/locales/${NAME}.pot
SOURCES =	bCNC/*.py \
		bCNC/controllers/*.py \
		bCNC/lib/*.py \
		bCNC/plugins/*.py

.PHONY: help pot tags clean upload

help:
	@echo "Targets: pot tags clean upload"

pot: ${POT}

${POT}: ${SOURCES}
	xgettext --from-code=UTF-8 --keyword=_ --keyword=N_ -d ${NAME} -o $@ $^

tags:
	ctags bCNC/*.py bCNC/controllers/*.py bCNC/lib/*.py bCNC/plugins/*.py

clean:
	git clean -Xf
	find bCNC -type d -name __pycache__ -prune -exec rm -rf {} +
	find bCNC \( -name '*.pyc' -o -name '*.pyo' \) -delete

upload:
	rm -f dist/*
	python3 setup.py sdist
	twine upload dist/*
	git tag -f pypi
	git push -f --tags up
