test:
	python --version
	pip install elasticsearch freezegun
	# Syntax check
	python -m py_compile ./scripts/curator.py
	python ./scripts/curator_test.py
