"""Versioned prompt registry for AI content generation.

Prompts are treated as product assets, not random strings. Every
template has an id, version, declared inputs, an output contract, a
list of safety rules, and an immutable template body. Registration is
done at import time by the modules under ``templates/``.

Public API:

- :class:`PromptTemplate`
- :class:`PromptInputSpec`
- :func:`get_prompt`
- :func:`list_prompts`
- :func:`list_prompt_ids`
- :func:`list_versions_for_family`
- :class:`PromptRegistryError`
- :class:`PromptDefinitionError`
- :class:`PromptRenderError`
"""

from scripts.ai.prompts.registry import (  # noqa: F401  re-export
    PromptDefinitionError,
    PromptInputSpec,
    PromptRegistryError,
    PromptRenderError,
    PromptTemplate,
    REQUIRED_SECTIONS,
    get_prompt,
    list_prompt_ids,
    list_prompts,
    list_versions_for_family,
)
