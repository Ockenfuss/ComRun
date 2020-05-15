unittest:
	python3 -m unittest discover -s test/unit
integrationtest:
	python3 -m unittest discover -s test/integration

.PHONY: unittest integrationtest
