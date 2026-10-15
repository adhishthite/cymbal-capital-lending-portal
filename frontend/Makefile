.PHONY: start dev test format lint clean check

start:
	bun run preview

dev:
	bun run dev

test:
	bun run test

format:
	bun run format

lint:
	bun run lint

clean:
	rm -rf dist node_modules/.vite

check: format lint test
