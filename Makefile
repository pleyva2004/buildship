# VISTA — Engineer B targets (run from repo root)

.PHONY: agent agent-live app

agent:            ## terminal chat with the VISTA agent (mock backend by default)
	python3 -m agent.loop

agent-live:       ## same, forced live against Nebius (needs NEBIUS_API_KEY in .env)
	VISTA_BACKEND=live python3 -m agent.loop

app:              ## dev server; symlinks /assets so the app reads A's files by convention
	mkdir -p app/public
	ln -sfn ../../assets app/public/assets
	cd app && npm run dev
