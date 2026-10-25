"""Unit tests for Langfuse observability and privacy masking."""

import pytest
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

from smart_notes.observability import mask_data, get_langfuse_callback
from smart_notes.config import settings


def test_mask_data_function():
    # String masking
    assert mask_data("secret message") == "[MASKED]"

    # Dict masking
    data = {"prompt": "tell me a secret", "metadata": {"user": "alice"}}
    expected = {"prompt": "[MASKED]", "metadata": {"user": "[MASKED]"}}
    assert mask_data(data) == expected

    # List masking
    data = ["secret1", "secret2"]
    assert mask_data(data) == ["[MASKED]", "[MASKED]"]

    # Tuple masking
    data = ("secret1", "secret2")
    assert mask_data(data) == ("[MASKED]", "[MASKED]")

    # Set masking
    data = {"secret1"}
    assert mask_data(data) == {"[MASKED]"}

    # Nested masking
    data = {"messages": [{"content": "hi"}]}
    expected = {"messages": [{"content": "[MASKED]"}]}
    assert mask_data(data) == expected

    # Non-string primitives preserved
    assert mask_data(123) == 123
    assert mask_data(True) is True
    assert mask_data(None) is None
    assert mask_data({"count": 5}) == {"count": 5}


def test_get_langfuse_callback_disabled_by_default():
    with patch_settings(tracing=False, pk="pk-123", sk="sk-123"):
        assert get_langfuse_callback() is None

    with patch_settings(tracing=True, pk=None, sk="sk-123"):
        assert get_langfuse_callback() is None

    with patch_settings(tracing=True, pk="pk-123", sk=None):
        assert get_langfuse_callback() is None


def test_get_langfuse_callback_enabled():
    with patch_settings(tracing=True, pk="pk-123", sk="sk-123"):
        with patch_settings_mask(True):
            callback = get_langfuse_callback()
            assert isinstance(callback, CallbackHandler)


def test_mask_data_integration_with_langfuse_client():
    exporter = InMemorySpanExporter()
    client = Langfuse(
        public_key="pk-test",
        secret_key="sk-test",
        base_url="https://cloud.langfuse.com",
        mask=mask_data,
        span_exporter=exporter,
        tracing_enabled=True,
    )

    span = client.start_observation(
        name="test-span",
        as_type="span",
        input={"prompt": "sensitive user prompt"},
        output={"answer": "sensitive user answer"},
    )
    span.end()
    client.flush()

    finished = exporter.get_finished_spans()
    assert len(finished) == 1
    attrs = finished[0].attributes

    assert attrs["langfuse.observation.input"] == '{"prompt": "[MASKED]"}'
    assert attrs["langfuse.observation.output"] == '{"answer": "[MASKED]"}'


def patch_settings(tracing: bool, pk: str | None, sk: str | None):
    from unittest.mock import patch
    class Context:
        def __enter__(self):
            self.p1 = patch.object(settings, "langfuse_tracing_enabled", tracing)
            self.p2 = patch.object(settings, "langfuse_public_key", pk)
            self.p3 = patch.object(settings, "langfuse_secret_key", sk)
            self.p1.start()
            self.p2.start()
            self.p3.start()
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            self.p3.stop()
            self.p2.stop()
            self.p1.stop()
    return Context()


def patch_settings_mask(mask: bool):
    from unittest.mock import patch
    class Context:
        def __enter__(self):
            self.p = patch.object(settings, "langfuse_mask_data", mask)
            self.p.start()
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            self.p.stop()
    return Context()
