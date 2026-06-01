"""Meta connector scaffolding.

The modules in this package cover Facebook, Instagram, and Threads setup
readiness only. They do not call real Meta APIs, exchange tokens, store raw
tokens, publish posts, fetch comments, or fetch analytics by default.
"""

from scripts.connectors.meta.facebook import FacebookConnector
from scripts.connectors.meta.instagram import InstagramConnector
from scripts.connectors.meta.threads import ThreadsConnector

__all__ = ["FacebookConnector", "InstagramConnector", "ThreadsConnector"]
