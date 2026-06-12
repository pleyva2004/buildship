# VISTA — Engineer B targets (run from repo root)
#
# MODEL shorthand for any *-live target:  make agent-live MODEL=deepseek
#   deepseek -> DeepSeek-V3.2-fast · qwen -> Qwen3.5-397B-A17B-fast
#   llama -> Llama-3.3-70B (default) · or pass a full Nebius model id
MODEL_deepseek = deepseek-ai/DeepSeek-V3.2-fast
MODEL_qwen     = Qwen/Qwen3.5-397B-A17B-fast
MODEL_llama    = meta-llama/Llama-3.3-70B-Instruct
MODEL_ENV      = $(if $(MODEL),NEBIUS_MODEL=$(or $(MODEL_$(MODEL)),$(MODEL)))

.PHONY: agent agent-live app seed seed-live serve serve-live deps listings listings-live interview interview-live test

deps:             ## install backend deps (fastapi, uvicorn, openai-agents)
	python3 -m pip install -r requirements.txt

test:             ## smoke tests — all mock, zero keys, zero network
	python3 -m pytest tests/ -q

listings:         ## B2 discovery -> assets/listings/index.draft.json (mock tavily, zero keys)
	python3 -m agent.listings

listings-live:    ## same, real Tavily search + extract (needs TAVILY_API_KEY in .env)
	TAVILY_BACKEND=live python3 -m agent.listings

serve:            ## agent API on :8001 (mock backends by default; docs at /docs)
	python3 -m uvicorn agent.server:app --port 8001 --reload

serve-live:       ## agent API, everything live (MODEL=deepseek|qwen|llama|<id>)
	$(MODEL_ENV) VISTA_BACKEND=live python3 -m uvicorn agent.server:app --port 8001

seed:             ## flatten profiles -> memories (mock; sanity check)
	python3 -m agent.seed

seed-live:        ## wipe + re-seed real mem0 with both profiles
	MEM0_BACKEND=live python3 -m agent.seed

interview:        ## terminal run of the getting-to-know-you interview (mock)
	python3 -m agent.interview

interview-live:   ## same, live planner on Nebius (MODEL=deepseek|qwen|llama|<id>)
	$(MODEL_ENV) VISTA_BACKEND=live python3 -m agent.interview

agent:            ## terminal chat with the VISTA agent (mock backend by default)
	python3 -m agent.loop

agent-live:       ## same, forced live (MODEL=deepseek|qwen|llama|<id>)
	$(MODEL_ENV) VISTA_BACKEND=live python3 -m agent.loop

app:              ## dev server; symlinks /assets so the app reads A's files by convention
	mkdir -p app/public
	ln -sfn ../../assets app/public/assets
	cd app && npm run dev
