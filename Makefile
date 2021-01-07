unittest:
	python3 -m unittest discover -s test/unit
integrationtest:
	[ -h libRadtranData ] || ( echo 'For integrationtest, libRadtran data must be available in the folder libRadtranData. Please create a link from the "libRadtran/data" directory to "ComRun/libRadtranData".' && exit 1 )
	python3 -m unittest discover -s test/integration

.PHONY: unittest integrationtest
