"""Prompt registry core types and lookup functions.

Templates live in ``scripts/ai/prompts/templates/`` as one file per
template version. Each file exposes a module-level ``TEMPLATE`` constant.
This module imports them all and exposes lookup helpers.

Design notes:

- Placeholders use ``{{ name }}`` so template bodies can contain literal
  curly braces in JSON examples without conflict with ``str.format``.
- ``PromptTemplate.__post_init__`` validates that every required input
  appears in the template body and that the template body never
  references an undeclared variable.
- Required section headers (``ROLE``, ``GOAL``, ``CONTEXT``,
  ``INPUTS``, ``CONSTRAINTS``, ``SAFETY RULES``, ``OUTPUT FORMAT``,
  ``ACCEPTANCE CRITERIA``) are also checked at construction time, so a
  malformed template fails to import.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

REQUIRED_SECTIONS: tuple[str, ...] = (
    "ROLE",
    "GOAL",
    "CONTEXT",
    "INPUTS",
    "CONSTRAINTS",
    "SAFETY RULES",
    "OUTPUT FORMAT",
    "ACCEPTANCE CRITERIA",
)

_PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")
_VERSION_RE = re.compile(r"^v\d+$")


class PromptRegistryError(RuntimeError):
    """Raised when registry lookup fails."""


class PromptDefinitionError(RuntimeError):
    """Raised when a template is constructed incorrectly."""


class PromptRenderError(RuntimeError):
    """Raised when rendering a template fails (missing variables, etc.)."""


@dataclass(frozen=True)
class PromptInputSpec:
    """Describes one variable a prompt template accepts."""

    name: str
    description: str
    required: bool = True
    type_hint: str = "string"
    example: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise PromptDefinitionError("PromptInputSpec.name is required.")
        if not _PLACEHOLDER_RE.fullmatch("{{ " + self.name + " }}"):
            raise PromptDefinitionError(
                f"PromptInputSpec.name must be a valid identifier: {self.name!r}"
            )
        if not isinstance(self.description, str) or not self.description.strip():
            raise PromptDefinitionError(
                f"PromptInputSpec.description is required for input {self.name!r}."
            )


def _format_value(value: Any) -> str:
    if value is None:
        return "[not provided]"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple)):
        if not value:
            return "[none listed]"
        return "\n".join(f"- {item}" for item in value)
    if isinstance(value, dict):
        if not value:
            return "[none listed]"
        return "\n".join(f"- {key}: {val}" for key, val in value.items())
    return str(value)


@dataclass(frozen=True)
class PromptTemplate:
    """One versioned prompt template.

    The ``id`` is the canonical lookup key (for example
    ``"platform_post_generator_v1"``). The ``family`` (everything before
    the trailing ``_v<n>``) groups versions of the same prompt.
    """

    id: str
    name: str
    version: str
    description: str
    expected_inputs: tuple[PromptInputSpec, ...]
    output_contract: str
    safety_rules: tuple[str, ...]
    template: str
    notes: str = ""
    created_at: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise PromptDefinitionError("PromptTemplate.id is required.")
        if not isinstance(self.name, str) or not self.name.strip():
            raise PromptDefinitionError("PromptTemplate.name is required.")
        if not isinstance(self.version, str) or not _VERSION_RE.fullmatch(self.version):
            raise PromptDefinitionError(
                f"PromptTemplate.version must look like 'v1', 'v2', ...; got {self.version!r}."
            )
        if not self.id.endswith("_" + self.version):
            raise PromptDefinitionError(
                f"PromptTemplate.id {self.id!r} must end with '_' + version {self.version!r}."
            )
        if not isinstance(self.description, str) or not self.description.strip():
            raise PromptDefinitionError(f"PromptTemplate {self.id!r}: description is required.")
        if not isinstance(self.template, str) or not self.template.strip():
            raise PromptDefinitionError(f"PromptTemplate {self.id!r}: template body is required.")
        if not isinstance(self.expected_inputs, tuple):
            raise PromptDefinitionError(
                f"PromptTemplate {self.id!r}: expected_inputs must be a tuple."
            )
        if not isinstance(self.safety_rules, tuple):
            raise PromptDefinitionError(
                f"PromptTemplate {self.id!r}: safety_rules must be a tuple."
            )
        if not self.safety_rules:
            raise PromptDefinitionError(
                f"PromptTemplate {self.id!r}: at least one safety rule is required."
            )

        declared_names = {spec.name for spec in self.expected_inputs}
        if len(declared_names) != len(self.expected_inputs):
            raise PromptDefinitionError(
                f"PromptTemplate {self.id!r}: duplicate input names."
            )

        placeholders = set(_PLACEHOLDER_RE.findall(self.template))
        undeclared = placeholders - declared_names
        if undeclared:
            raise PromptDefinitionError(
                f"PromptTemplate {self.id!r}: template references undeclared variable(s): "
                f"{sorted(undeclared)}"
            )

        required_names = {spec.name for spec in self.expected_inputs if spec.required}
        required_missing = required_names - placeholders
        if required_missing:
            raise PromptDefinitionError(
                f"PromptTemplate {self.id!r}: required input(s) never used in template body: "
                f"{sorted(required_missing)}"
            )

        for section in REQUIRED_SECTIONS:
            if section not in self.template:
                raise PromptDefinitionError(
                    f"PromptTemplate {self.id!r}: template missing required section header "
                    f"{section!r}."
                )

    @property
    def family(self) -> str:
        suffix = "_" + self.version
        return self.id[: -len(suffix)] if self.id.endswith(suffix) else self.id

    def required_input_names(self) -> tuple[str, ...]:
        return tuple(spec.name for spec in self.expected_inputs if spec.required)

    def optional_input_names(self) -> tuple[str, ...]:
        return tuple(spec.name for spec in self.expected_inputs if not spec.required)

    def render(self, variables: Optional[dict[str, Any]] = None) -> str:
        """Render the template with the supplied variables.

        Required variables that are missing raise :class:`PromptRenderError`.
        Optional variables that are omitted render as ``[not provided]``
        and lists/dicts render as bullet lists.
        """
        provided = dict(variables or {})
        declared = {spec.name for spec in self.expected_inputs}

        unknown_keys = set(provided) - declared
        if unknown_keys:
            raise PromptRenderError(
                f"PromptTemplate {self.id!r}: unknown variable(s) supplied: "
                f"{sorted(unknown_keys)}"
            )

        required = {spec.name for spec in self.expected_inputs if spec.required}
        missing_required = [name for name in required if name not in provided]
        if missing_required:
            raise PromptRenderError(
                f"PromptTemplate {self.id!r}: missing required variable(s): "
                f"{sorted(missing_required)}"
            )

        merged: dict[str, Any] = {}
        for spec in self.expected_inputs:
            merged[spec.name] = provided.get(spec.name, None)

        def _replace(match: re.Match[str]) -> str:
            name = match.group(1)
            return _format_value(merged.get(name))

        return _PLACEHOLDER_RE.sub(_replace, self.template)

    def to_metadata(self) -> dict[str, Any]:
        """Return a logging- and UI-safe metadata snapshot (no full template body)."""
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "family": self.family,
            "description": self.description,
            "expected_inputs": [
                {
                    "name": spec.name,
                    "description": spec.description,
                    "required": spec.required,
                    "type_hint": spec.type_hint,
                    "example": spec.example,
                }
                for spec in self.expected_inputs
            ],
            "output_contract": self.output_contract,
            "safety_rules": list(self.safety_rules),
            "notes": self.notes,
            "created_at": self.created_at,
        }


def _build_registry() -> dict[str, PromptTemplate]:
    # Import templates lazily inside the function to avoid circular imports.
    from scripts.ai.prompts.templates.caption_variants_generator_v1 import (
        TEMPLATE as caption_variants_v1,
    )
    from scripts.ai.prompts.templates.comment_reply_suggestion_v1 import (
        TEMPLATE as comment_reply_v1,
    )
    from scripts.ai.prompts.templates.content_strategy_brief_v1 import (
        TEMPLATE as content_strategy_v1,
    )
    from scripts.ai.prompts.templates.draft_improvement_v1 import (
        TEMPLATE as draft_improvement_v1,
    )
    from scripts.ai.prompts.templates.hashtag_generator_v1 import (
        TEMPLATE as hashtag_v1,
    )
    from scripts.ai.prompts.templates.platform_post_generator_v1 import (
        TEMPLATE as platform_post_v1,
    )
    from scripts.ai.prompts.templates.safety_review_v1 import (
        TEMPLATE as safety_review_v1,
    )

    templates: tuple[PromptTemplate, ...] = (
        content_strategy_v1,
        platform_post_v1,
        caption_variants_v1,
        hashtag_v1,
        safety_review_v1,
        draft_improvement_v1,
        comment_reply_v1,
    )
    registry: dict[str, PromptTemplate] = {}
    for template in templates:
        if template.id in registry:
            raise PromptRegistryError(
                f"Duplicate prompt id in registry: {template.id!r}"
            )
        registry[template.id] = template
    return registry


_REGISTRY: Optional[dict[str, PromptTemplate]] = None


def _registry() -> dict[str, PromptTemplate]:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = _build_registry()
    return _REGISTRY


def get_prompt(prompt_id: str) -> PromptTemplate:
    """Look up a template by id. Raises PromptRegistryError on miss."""
    if not isinstance(prompt_id, str):
        raise PromptRegistryError(f"prompt_id must be a string, got {type(prompt_id).__name__}.")
    key = prompt_id.strip()
    registry = _registry()
    if key not in registry:
        raise PromptRegistryError(
            f"Unknown prompt id: {prompt_id!r}. Known ids: {sorted(registry)}."
        )
    return registry[key]


def list_prompts() -> tuple[PromptTemplate, ...]:
    """Return every registered template, sorted by id."""
    return tuple(sorted(_registry().values(), key=lambda template: template.id))


def list_prompt_ids() -> tuple[str, ...]:
    return tuple(sorted(_registry().keys()))


def list_versions_for_family(family: str) -> tuple[PromptTemplate, ...]:
    """Return every template that belongs to a prompt family, sorted by version."""
    return tuple(
        sorted(
            (template for template in _registry().values() if template.family == family),
            key=lambda template: template.version,
        )
    )
