"""One-time B2 listing discovery (design 03 + 07 §3).

  make listings        # mock — canned Tavily, zero keys
  make listings-live   # real Tavily search + extract

Writes assets/listings/index.draft.json and prints hero photo URLs for manual
download. NEVER touches the frozen assets/listings/index.json — promoting draft
material into the inventory is a deliberate human edit (the H4 freeze).
"""

import json

from agent import config
from agent.clients import tavily_client

QUERY = "4 bedroom house for sale Austin TX bright open plan fenced yard walkable"
DRAFT_PATH = config.ASSETS_DIR / "listings" / "index.draft.json"


def main() -> None:
    mode = config.backend("tavily")
    print(f"[{mode}] tavily search: {QUERY!r}")
    candidates = tavily_client.search(QUERY, max_results=5)
    for i, c in enumerate(candidates):
        print(f"  {i}. ({c['score']:.2f}) {c['title']}\n     {c['url']}")
    if not candidates:
        print("No candidates — nothing written.")
        return

    hero = candidates[0]
    print(f"\n[{mode}] extracting hero candidate: {hero['url']}")
    try:
        page = tavily_client.extract(hero["url"])
    except Exception as exc:  # portals often block extraction (design 03 §3)
        print(f"  extract failed ({exc}) — keeping search candidates, photos go manual")
        page = {"url": hero["url"], "raw_content": "", "images": []}

    DRAFT_PATH.write_text(json.dumps({
        "_comment": "Tavily discovery draft — review, then hand-merge the keepers "
                    "into index.json. The frozen index is never auto-written.",
        "query": QUERY,
        "candidates": candidates,
        "hero_extract": page,
    }, indent=2))
    print(f"\nwrote {DRAFT_PATH.relative_to(config.REPO_ROOT)}")

    if page["images"]:
        print("\nHero photo URLs — download manually, save as "
              "assets/listings/hero/raw/hero__<room>.jpg (normalize: JPEG, max 2048px):")
        for url in page["images"]:
            print(f"  {url}")
    else:
        print("\nNo photos extracted — manual download from the listing page (sanctioned, CLAUDE.md §5).")


if __name__ == "__main__":
    main()
