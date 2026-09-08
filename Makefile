.PHONY: demo test api web install e2e e2e-install e2e-cloud compose

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

e2e-install:
	cd apps/web && npm install && npx playwright install --with-deps chromium

e2e:
	cd apps/web && npx playwright test

e2e-cloud:
	cd apps/web && npx playwright test --config=playwright.cloud.config.ts

compose:
	docker compose up --build
