"""OpenAI provider stub.

This module does not import the OpenAI SDK. Constructor reads gate
environment variables and stores their state. ``generate_bundle`` always
raises ``ProviderDisabledError`` in Batch 3 because real provider calls
are off by policy.

A future batch may add a real implementation behind these same gates.
"""

from __future__ import annotations

from scripts.ai.providers.base import RealProviderStub


class OpenAIProvider(RealProviderStub):
    name = "openai"
    label = "OpenAI"
    api_key_env = "OPENAI_API_KEY"
    api_key_required = True
    not_implemented_message = (
        "OpenAI adapter is scaffolded but not yet implemented. "
        "Batch 3 keeps real provider calls off by policy."
    )
