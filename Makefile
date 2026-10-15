.PHONY: start dev test format lint clean check

start:
	cd frontend && bun run build
	cd backend && $(MAKE) start

dev:
	npx --yes concurrently "cd backend && $(MAKE) dev" "cd frontend && $(MAKE) dev"

test:
	cd backend && $(MAKE) test
	cd frontend && $(MAKE) test

format:
	cd backend && $(MAKE) format
	cd frontend && $(MAKE) format

lint:
	cd backend && $(MAKE) lint
	cd frontend && $(MAKE) lint

clean:
	cd backend && $(MAKE) clean
	cd frontend && $(MAKE) clean

check: format lint test
