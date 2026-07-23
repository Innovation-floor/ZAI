.PHONY: up down logs rebuild test smoke clean

up:       ## build and start the stack
	docker compose up --build -d
	@echo "ZAI running at http://localhost:$${WEB_PORT:-8080}  (API docs: http://localhost:$${API_PORT:-8010}/api/docs)"

down:
	docker compose down

logs:
	docker compose logs -f --tail=100

rebuild:
	docker compose build --no-cache && docker compose up -d

smoke:    ## verify the running stack answers the scripted demo questions
	@bash ops/smoke.sh

test:     ## run the backend test suite locally
	cd backend && python -m pytest -q

clean:
	docker compose down -v --rmi local
