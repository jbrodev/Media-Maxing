"""Anthropic provider stub.

This module does not import the Anthropic SDK. Constructor reads gate
environment variables and stores their state. ``generate_bundle`` always
raises ``ProviderDisabledError`` in Batch 3 because real provider calls
are off by policy.
"""

from __future__ import annotations

from scripts.ai.providers.base import RealProviderStub


class AnthropicProvider(RealProviderStub):
    name = "anthropic"
    label = "Anthropic"
    api_key_env = "ANTHROPIC_API_KEY"
    api_key_required = True
    not_implemented_message = (
        "Anthropic adapter is scaffolded but not yet implemented. "
        "Batch 3 keeps real provider calls off by policy."
    )
