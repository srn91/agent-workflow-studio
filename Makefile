.PHONY: demo serve test lint verify clean

demo:
	python3 -m app.cli demo

serve:
	uvicorn app.main:app --host 127.0.0.1 --port 8005

test:
	pytest -q

lint:
	ruff check app tests

verify: lint test demo

clean:
	rm -rf generated
