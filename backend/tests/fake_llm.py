"""Reusable fake OpenAI client for offline LLM tests.

The whole trial-extraction + llm-router path funnels through a single module-level
symbol, so one monkeypatch makes every LLM call deterministic and offline:

    from .fake_llm import make_fake_openai
    monkeypatch.setattr(
        "backend.src.utils.info_extraction.OpenAI",
        make_fake_openai('{"name": "Ada"}'),
    )

The fake implements the bits the real code reads: ``chat.completions.create``
(returns ``choices[0].message.{content,reasoning_content,refusal}``,
``finish_reason`` and ``usage.model_dump()``) and ``models.list()`` (returns
``.data`` of objects with ``.id``) for the ``/llm/models`` + ``/test-connection``
endpoints. It is also a context manager, matching the ``with OpenAI(...) as client``
usage in ``extract_info_single_doc``.
"""

import json


class _FakeMessage:
    def __init__(self, content, *, reasoning=None, refusal=None):
        self.content = content
        self.reasoning_content = reasoning
        self.refusal = refusal


class _FakeChoice:
    def __init__(self, content, *, finish_reason="stop", reasoning=None, refusal=None):
        self.message = _FakeMessage(content, reasoning=reasoning, refusal=refusal)
        self.finish_reason = finish_reason


class _FakeUsage:
    def model_dump(self):
        return {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}


class _FakeCompletion:
    def __init__(self, content, *, finish_reason="stop", reasoning=None, refusal=None):
        self.choices = [
            _FakeChoice(
                content,
                finish_reason=finish_reason,
                reasoning=reasoning,
                refusal=refusal,
            )
        ]
        self.usage = _FakeUsage()


class _FakeModel:
    def __init__(self, model_id):
        self.id = model_id


class _FakeModelList:
    def __init__(self, ids):
        self.data = [_FakeModel(i) for i in ids]


def _as_str(value):
    return value if isinstance(value, str) else json.dumps(value)


def make_fake_openai(
    content="{}",
    *,
    models=("gpt-4o-mini", "gpt-4o"),
    finish_reason="stop",
    reasoning=None,
    refusal=None,
    completion_hook=None,
):
    """Return a fake ``OpenAI`` class suitable for ``monkeypatch.setattr``.

    ``content`` is the chat-completion message content (dicts are JSON-encoded).
    ``completion_hook(**kwargs)`` may return per-call content to vary output by
    document (it receives the same kwargs passed to ``chat.completions.create``).
    ``models`` is the list of model ids returned by ``models.list()``.
    """
    default_content = _as_str(content)

    class _FakeCompletions:
        def create(self, **kwargs):
            body = completion_hook(**kwargs) if completion_hook else default_content
            return _FakeCompletion(
                _as_str(body),
                finish_reason=finish_reason,
                reasoning=reasoning,
                refusal=refusal,
            )

    class _FakeChat:
        def __init__(self):
            self.completions = _FakeCompletions()

    class _FakeModels:
        def list(self):
            return _FakeModelList(models)

    class _FakeOpenAI:
        def __init__(self, *args, **kwargs):
            self.chat = _FakeChat()
            self.models = _FakeModels()

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    return _FakeOpenAI
