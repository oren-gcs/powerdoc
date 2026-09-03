.PHONY: demo test api web install

install:
	python3 -m pip install -r apps/api/requirements.txt
	cd apps/web && npm install

api:
	cd apps/api && PYTHONPATH=. python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

web:
	cd apps/web && npm run dev

demo: install
	mkdir -p data/storage
	cd apps/api && PYTHONPATH=. python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
	cd apps/web && npm run dev

test:
	cd apps/api && PYTHONPATH=. python3 -m pytest -q tests

compose:
	docker compose up --build
