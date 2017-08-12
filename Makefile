PYTHON_FILES = $(shell find . -name "*.py" -not -path "./env/*")


.PHONY: all translate translateSetup translateUpdate translateCompile

all:


translateExctract: $(PYTHON_FILES)
	pybabel extract -F babel.cfg -k lazy_gettext -o translations/messages.pot .


translateSetup: translateExctract
	pybabel init -i translations/messages.pot -d translations -l nl


translateUpdate: translateExctract
	pybabel update -i translations/messages.pot -d translations


translateCompile:
	pybabel compile -d translations

