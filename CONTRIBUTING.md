# Contributing to PromptBeacon

Thanks for helping. Bug reports, docs fixes, new metadata sources and new providers are
all welcome.

## Set up

```bash
git clone https://github.com/yotambraun/promptbeacon
cd promptbeacon
uv sync --all-extras
```

Everything below runs without API keys: the test suite uses the keyless demo client and
mocked HTTP.

## Before you open a pull request

```bash
uv run pytest                 # tests
uv run ruff check .           # lint
uv run ruff format --check .  # formatting (also formats code blocks in Markdown)
uv run mypy src               # types
```

- Add a test with every bug fix, one that fails before the fix.
- Keep the public API backward compatible: add options rather than changing existing
  ones.
- Never make real provider calls in tests. Use `Beacon(...).demo()`, `MockLLMClient`, or
  patch `LiteLLMClient.complete`. Project metadata tests pass a fake `http` callable.
- If you change something users see, update `README.md`, the docs in `docs/` and
  `CHANGELOG.md`. Build the docs with `uv run mkdocs build --strict`.

## Good first contributions

- **A new project source** (crates.io, Hugging Face, Packagist, ...): subclass
  `promptbeacon.projects.MetadataSource`, implement `fetch()`, and register it with
  `register_source`. See `docs/projects.md`.
- **Prompt templates** for an industry you know (`promptbeacon/prompts/templates.py`).
- Ideas in [TODO.md](TODO.md).

## Reporting issues

Please include the command or code you ran, the PromptBeacon version
(`python -c "import promptbeacon; print(promptbeacon.__version__)"`), and whether the
scan was `demo`, `base_model` or `api_grounded` (shown in every report). Never paste API
keys.
