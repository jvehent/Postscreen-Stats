PREFIX = /usr/local
PYTHON_SCRIPTS = postscreen_stats.py
SHELL_SCRIPTS = lasso-update.sh rbl-check.sh
.PHONY: all
all: check

# Run one or more Python syntax checkers on scripts
# Comment out any that you don't have installed
check:
	$(foreach script,$(SHELL_SCRIPTS),bash -n $(script))
	flake8 $(PYTHON_SCRIPTS)
	pep8 $(PYTHON_SCRIPTS)
	pyflakes $(PYTHON_SCRIPTS)

# Remove Python compiled file
clean:
	rm -fv $(PYTHON_SCRIPTS)c

# Compile Python scripts
compile:
	python -m py_compile $(PYTHON_SCRIPTS)

# TODO: What to do with pyc Python compiled file
install:
	install $(PYTHON_SCRIPTS) $(PREFIX)/bin
	install $(SHELL_SCRIPTS) $(PREFIX)/bin

