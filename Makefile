evertest:
	while /bin/true; do inotifywait -e create -e modify *.rst **/*.py; sphinx-build -b html . ./_build; clear; nosetests --cov filternaut --rednose && echo '' && flake8; done
