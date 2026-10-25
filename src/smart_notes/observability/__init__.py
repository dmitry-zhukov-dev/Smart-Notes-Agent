"""Langfuse observability and privacy masking for the Smart Notes Agent.

This module exposes a single factory, :func:`get_langfuse_callback`, that the
application wires into LangGraph execution. It is safe to call at any time:

* When tracing is disabled or credentials are missing it returns ``None``.
* When tracing is enabled and credentials are present it returns a
  :class:`langfuse.langchain.CallbackHandler` backed by a
  :class:`langfuse.Langfuse` client that has been configured with the SDK's
  supported ``mask`` hook.

The installed Langfuse SDK (``langfuse>=3.8.0``) exposes a ``mask`` keyword on
:class:`langfuse.Langfuse` (a ``MaskFunction`` protocol). That hook is applied
to every ``input`` / ``output`` / ``metadata`` attribute the SDK writes to an
observation before the data is exported, so sensitive payloads never leave the
process. The LangChain :class:`CallbackHandler` itself only accepts
``public_key`` and ``trace_context``; it looks up the singleton client created
by :func:`langfuse._client.get_client.get_client`, which preserves the mask
configuration set on the originating :class:`Langfuse` instance.
"""

from __future__ import annotations

from typing import Any

from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

from smart_notes.config import settings

__all__ = ["mask_data", "get_langfuse_callback"]


def mask_data(data: Any) -> Any:
    """Recursively replace every string leaf in ``data`` with ``"[MASKED]"``.

    The function preserves the original data structure (dicts, lists, tuples,
    sets, primitives) so that masked payloads remain valid JSON-serializable
    structures. It is the privacy hook consumed by Langfuse when
    ``settings.langfuse_mask_data`` is enabled.

    Args:
        data: Any value to mask. Strings are replaced; dicts, lists, tuples
            and sets are traversed recursively; everything else is returned
            unchanged.

    Returns:
        The masked value, structurally identical to the input.
    """
    if isinstance(data, str):
        return "[MASKED]"
    if isinstance(data, dict):
        return {key: mask_data(value) for key, value in data.items()}
    if isinstance(data, list):
        return [mask_data(item) for item in data]
    if isinstance(data, tuple):
        return tuple(mask_data(item) for item in data)
    if isinstance(data, set):
        return {mask_data(item) for item in data}
    return data


def _build_langfuse_client() -> Langfuse:
    """Create the Langfuse client with the configured mask hook (if any)."""
    mask: Any = mask_data if settings.langfuse_mask_data else None

    return Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        base_url=settings.langfuse_base_url,
        mask=mask,
    )


def get_langfuse_callback() -> CallbackHandler | None:
    """Return a Langfuse callback handler, or ``None`` when tracing is off.

    Tracing is disabled when:

    * :attr:`settings.langfuse_tracing_enabled` is ``False``, or
    * the Langfuse public or secret key is missing.

    When enabled, the function creates a :class:`langfuse.Langfuse` client
    (registering it with the SDK's singleton resource manager under the
    configured public key) and then constructs a LangChain
    :class:`CallbackHandler`. The handler resolves to the same client, so the
    configured ``mask`` hook is applied to every observation attribute the SDK
    exports.

    Returns:
        A configured :class:`CallbackHandler`, or ``None``.
    """
    if not settings.langfuse_tracing_enabled:
        return None

    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        return None

    # Register the client with the SDK's singleton manager under the
    # configured public key. The CallbackHandler resolves to this same
    # instance via get_client(public_key=...), which preserves the mask
    # configuration set here.
    _build_langfuse_client()

    return CallbackHandler(public_key=settings.langfuse_public_key)