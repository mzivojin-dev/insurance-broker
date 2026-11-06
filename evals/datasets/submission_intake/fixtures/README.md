Fixture PDFs come from the synthetic agency generator in `data/seed` (episode 2).
Each `<name>.pdf` needs a hand-checked `<name>.expected.json` with the values the agent must extract.
Until the PDFs exist, these cases fail with "no JSON output", which is the expected red state.
