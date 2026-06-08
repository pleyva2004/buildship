"""List the models your Nebius account serves (run from a networked terminal).

    uv run --python /opt/homebrew/opt/python@3.12/bin/python3.12 model_list.py

Use this to find the exact NEBIUS_MODEL id to put in .env — the default
`deepseek-ai/DeepSeek-V3` may 404 if your account exposes a different slug.
"""

import os
import sys

from dotenv import load_dotenv

load_dotenv()

# Substrings that flag a model as a good codegen pick, so they're easy to spot.
_CODER_HINTS = ("coder", "deepseek", "qwen", "code", "instruct")


def main() -> int:
    api_key = os.environ.get("NEBIUS_API_KEY")
    if not api_key:
        print("NEBIUS_API_KEY is not set. Fill it into .env first.")
        return 1

    from openai import OpenAI

    base_url = os.environ.get("NEBIUS_BASE_URL", "https://api.studio.nebius.ai/v1")
    client = OpenAI(api_key=api_key, base_url=base_url)

    try:
        models = sorted(m.id for m in client.models.list().data)
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to list models from {base_url}:\n  {exc!r}")
        print("\nIf this is a 403/ProxyError you're behind a blocking proxy — "
              "run this from a normal terminal. A 401 means the API key is wrong.")
        return 2

    current = os.environ.get("NEBIUS_MODEL", "")
    print(f"{len(models)} models available at {base_url}\n")

    likely = [m for m in models if any(h in m.lower() for h in _CODER_HINTS)]
    if likely:
        print("--- likely codegen models (set one as NEBIUS_MODEL) ---")
        for m in likely:
            print(f"  {'* ' if m == current else '  '}{m}")
        print()

    print("--- all models ---")
    for m in models:
        print(f"  {'* ' if m == current else '  '}{m}")

    if current:
        status = "OK, present" if current in models else "NOT in this list -> 404"
        print(f"\ncurrent NEBIUS_MODEL = {current!r}  [{status}]")
    else:
        print("\nNEBIUS_MODEL is unset; pick one above and add it to .env.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
