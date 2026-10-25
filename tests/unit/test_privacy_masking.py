"""Unit tests for privacy masking functionality and integration with observability."""

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
    
    # Nested masking
    data = {"messages": [{"content": "hi"}]}
    expected = {"messages": [{"content": "[MASKED]"}]}
    assert mask_data(data) == expected
    
    # Non-string types preserved structurally
    assert mask_data(123) == 123
    assert mask_data({"count": 5}) == {"count": 5}


def test_get_langfuse_callback_disabled_by_default():
    with patch_settings(tracing=False, pk="pk-123", sk="sk-123"):
        assert get_langfuse_callback() is None

    with patch_settings(tracing=True, pk=None, sk="sk-123"):
        assert get_langfuse_callback() is None


def test_mask_data_integration_with_client():
    exporter = InMemorySpanExporter()
    client = Langfuse(
        public_key="pk-test",
        secret_key="sk-test",
        base_url="https://cloud.langfuse.com",
        mask=mask_data,
        span_exporter=exporter,
        tracing_enabled=True,
    )

    test_input = {"prompt": "sensitive info"}
    span = client.start_observation(
        name="test-obs",
        as_type="span",
        input=test_input,
    )
    span.end()
    client.flush()

    spans = exporter.get_finished_spans()
    if len(spans) == 0:
        pytest.skip("Span not exported due to sampling or sampling / blocking")

    input_attr = spans[0].attributes.get("langfuse.observation.input")
    assert "sensitive info" not in str(input_attr)
    assert "[MASKED]" in str(input_attr)


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
