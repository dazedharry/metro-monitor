# Metro output monitor

Collects Metro's RSS feed every three hours into a rolling 120-day archive and shows it as a dashboard.

## Set up (about 10 minutes)
1. Create a GitHub repository and upload this folder's contents.
2. Settings > Pages > Deploy from a branch > `main` / `/docs`.
3. Actions tab > "Update Metro monitor" > Run workflow. This creates the first archive.
4. Open the Pages address. The dashboard fills as history builds.

## Notes
- The feed only holds the latest items, so history starts on the first run. Three-hourly runs avoid gaps.
- Add section feeds to `feeds.txt` for fuller coverage. Check each opens in a browser first.
- If the workflow fails with a 403, Metro is blocking the GitHub runner. Run `python fetch_feed.py` on your own machine or a small server on a schedule instead, and commit `docs/data/stories.json`.
- Preview locally: `python fetch_feed.py` then `python -m http.server --directory docs`.
- Private repositories need a paid GitHub plan for Pages.
