# Claude Code & MCP

Use PromptBeacon from Claude Code, Cursor, or any client that speaks the
[Model Context Protocol](https://modelcontextprotocol.io). Ask "does AI recommend my
library?" in your editor and get the same numbers as the CLI.

## Claude Code plugin

The repository is also a plugin marketplace. In Claude Code:

```text
/plugin marketplace add yotambraun/promptbeacon
/plugin install promptbeacon@promptbeacon
```

The plugin starts the MCP server with [uv](https://docs.astral.sh/uv/)
(`uvx --from 'promptbeacon[mcp]' promptbeacon mcp`), so uv must be installed. It adds
three skills:

| Skill | What it does |
| --- | --- |
| `ai-visibility` | Checks whether AI assistants recommend a product or project and reports score, share of voice and how it was measured |
| `share-card` | Creates a README badge, shields.io JSON and light/dark share cards |
| `visibility-ci` | Adds a weekly or pull-request GitHub workflow (run it with `/promptbeacon:visibility-ci`) |

## Any MCP client

Install the extra and run the server over stdio:

```bash
pip install 'promptbeacon[mcp]'
promptbeacon mcp
```

Register it with Claude Code without the plugin:

```bash
claude mcp add promptbeacon -- uvx --from 'promptbeacon[mcp]' promptbeacon mcp
```

Or in a client's JSON configuration:

```json
{
  "mcpServers": {
    "promptbeacon": {
      "command": "uvx",
      "args": ["--from", "promptbeacon[mcp]", "promptbeacon", "mcp"],
      "env": {
        "OPENAI_API_KEY": "${OPENAI_API_KEY:-}",
        "ANTHROPIC_API_KEY": "${ANTHROPIC_API_KEY:-}"
      }
    }
  }
}
```

## Tools

Every tool is a thin wrapper over the Python API and returns compact JSON (no raw model
responses).

| Tool | Arguments | Returns |
| --- | --- | --- |
| `providers` | none | Which providers and Tavily are configured (`true`/`false`, never the key values) and the default mode |
| `scan` | `brand`, `category`, `competitors`, `providers`, `prompts`, `demo`, `grounded` | Score, share of voice and rank, presence, a per-brand table, top sources, models, prompts, cost, top recommendations, `measurement_tier` |
| `project_scan` | `project` (`github:owner/name`, `pypi:pkg`, `npm:pkg`), `category`, `competitors`, `providers`, `prompts`, `demo`, `infer_category` | The scan result plus a `project` object with the metadata and the guessed category and competitors, with their basis |
| `sources` | `brand`, `category`, `competitors`, `providers`, `demo`, `grounded` (default `true`) | The domains AI answers cite and whether each cites the brand |
| `share_assets` | `brand` or `project`, `category`, `competitors`, `providers`, `demo`, `output_dir`, `png` | Paths of `badge.svg`, `badge.json`, `card.svg`, `card-dark.svg` (and `card.png`), README snippets, and the summary |

A scan without a category returns a `warning` explaining that the prompts were generic.

## Keys and cost

Provider keys reach the server through its environment: the variables in your shell,
or the `env` block of the client configuration (the plugin maps each supported key
explicitly). Empty values count as not configured.

- With **no key** configured, tools default to the keyless demo and the result
  includes a `note` that says so. Nothing is billed.
- With keys, scans are real and billed to those keys; results include an estimated
  cost.
- Passing `demo: false` without any key is an error rather than a silent fallback.

The server writes nothing to stdout except the protocol. Under the plugin, PromptBeacon's
data directory is the plugin's data directory.
