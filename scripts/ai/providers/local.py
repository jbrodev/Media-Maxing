"""Local AI runtime provider stub.

This module does not import any local-LLM client. It is intended for a
future on-device or self-hosted runtime such as Ollama, llama.cpp,
LM Studio, or similar. Constructor reads gate environment variables and
stores their state. ``generate_bundle`` always raises
``ProviderDisabledError`` in Batch 3.

Configuration is read from ``LOCAL_AI_BASE_URL``. Because this points to
a local runtime rather than a cloud API, the safety gates still apply:
the local provider only activates when ``INTEGRATIONS_MODE`` is not
``mock`` and ``ENABLE_REAL_NETWORK_CALLS=true``.
"""

from __future__ import annotations

from scripts.ai.providers.base import RealProviderStub


class LocalProvider(RealProviderStub):
    name = "local"
    label = "Local AI runtime"
    api_key_env = "LOCAL_AI_BASE_URL"
    api_key_required = True
    not_implemented_message = (
        "Local AI adapter is scaffolded but not yet implemented. "
        "Batch 3 keeps real provider calls off by policy."
    )
