# packages/agent_core/src/agent_core/models.py
import os

REASONING = os.environ.get("AGENT_MODEL", "claude-sonnet-5-5")       # answers, tool use, SQL
FAST = os.environ.get("AGENT_FAST_MODEL", "claude-haiku-5-5")        # classify, route, judge drafts