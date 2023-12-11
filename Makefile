WHITE="\033[1;37m"
GREEN="\033[1;32m"
YELLOW="\033[1;33m"
CLEAN="\033[0m"

install:
	pip install --upgrade pip
	pip install -r requirements.txt

install-dev: install
	pip install -r requirements-dev.txt

test:
	@if [ "$(module)" = "" ]; then\
		echo $(WHITE)Starting tests for $(YELLOW)channel_app$(CLEAN)..$(CLEAN);\
		coverage erase;\
		coverage run -m unittest discover channel_app;\
    fi

	@if [ $(module) ]; then\
		echo $(WHITE)Starting tests for $(YELLOW)channel_app.$(module)$(CLEAN) $(WHITE)module..$(CLEAN);\
		coverage run -m unittest discover channel_app.$(module);\
    fi

coverage:
	@if [ "$(module)" = "" ]; then\
		coverage report $(extra);\
	fi;\

	@if [ $(module) ]; then\
		coverage report --include="channel_app/$(subst .,/,$(module))/*" $(extra);\
	fi;\

coverage-html:
	@if [ "$(module)" = "" ]; then\
		coverage html;\
	fi;\

	@if [ $(module) ]; then\
		coverage html --include="channel_app/$(subst .,/,$(module))/*";\
	fi;\

	@echo \\n$(GREEN)Detailed report generated successfully and it is accessible from \"file://$(PWD)/htmlcov/index.html\".

clean:
	coverage erase
	rm -rf htmlcov/
	@echo $(GREEN)Coverage related data files cleaned up!$(CLEAN)

check: clean test coverage coverage-html
	@echo $(GREEN)All tests passed!$(CLEAN)