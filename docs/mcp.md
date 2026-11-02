# Use from your AI assistant

PromptBeacon runs as an [MCP](https://modelcontextprotocol.io) server, so the assistant
you already use (Claude Code, Claude Desktop, Cursor, VS Code with GitHub Copilot,
Windsurf, Codex CLI, Gemini CLI) can measure whether AI recommends your project and then
reason about the result with you. PromptBeacon does the measuring: the same scans,
numbers and labels as the CLI, returned as JSON. Your assistant does the thinking: what
the numbers mean for your project, and what to do next.

Ask, for example:

- *"Does AI recommend this project? Compare it with its two main alternatives."*
- *"What would a real scan with Claude and GPT cost? Keep it under 5 cents."*
- *"Which sites do AI answers cite for python http clients, and do any cite us?"*
- *"Has our AI visibility changed since last month, and is the change real?"*
- *"Set this repository up for a weekly AI visibility check. Show me the plan first."*

## Before you start

Every setup below starts the server with [uv](https://docs.astral.sh/uv/)'s `uvx`, which
downloads PromptBeacon into a cached environment on first use; nothing else needs
installing. [Install uv](https://docs.astral.sh/uv/getting-started/installation/) if
`uvx --version` doesn't work. The command each client runs is:

```bash
uvx --from "promptbeacon[mcp]>=1.4.0" promptbeacon mcp
```

**No API key is needed to try it.** Without one, every tool uses keyless demo data,
costs nothing, and says so in its result. Add keys ([below](#keys-models-and-cost)) for
real measurements, which are billed to your own provider accounts.

## Set up your client

=== "Claude Code"

    **Plugin (recommended)**: adds the server and four [skills](#skills). In Claude
    Code:

    ```text
    /plugin marketplace add yotambraun/promptbeacon
    /plugin install promptbeacon@promptbeacon
    ```

    The plugin passes your shell's provider keys and `PROMPTBEACON_*_MODEL` variables
    to the server.

    **Server only**, for all your projects:

    ```bash
    claude mcp add --transport stdio --scope user promptbeacon -- uvx --from "promptbeacon[mcp]>=1.4.0" promptbeacon mcp
    ```

    Use `--scope project` instead to write a `.mcp.json` that your team shares. To pass
    keys from your shell without writing them into the file, use `${VAR:-}`
    references (put `--env` before `--transport`):

    ```bash
    claude mcp add --env 'OPENAI_API_KEY=${OPENAI_API_KEY:-}' --env 'ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}' --transport stdio --scope project promptbeacon -- uvx --from "promptbeacon[mcp]>=1.4.0" promptbeacon mcp
    ```

    which writes:

    ```json
    {
      "mcpServers": {
        "promptbeacon": {
          "type": "stdio",
          "command": "uvx",
          "args": ["--from", "promptbeacon[mcp]>=1.4.0", "promptbeacon", "mcp"],
          "env": {
            "OPENAI_API_KEY": "${OPENAI_API_KEY:-}",
            "ANTHROPIC_API_KEY": "${ANTHROPIC_API_KEY:-}"
          }
        }
      }
    }
    ```

    Check it with `claude mcp get promptbeacon`, or `/mcp` inside Claude Code.
    Docs: [Claude Code MCP](https://code.claude.com/docs/en/mcp).

=== "Claude Desktop"

    Open **Settings → Developer → Edit Config**, which opens
    `claude_desktop_config.json` (macOS: `~/Library/Application Support/Claude/`,
    Windows: `%APPDATA%\Claude\`, Linux: `~/.config/Claude/`), and add:

    ```json
    {
      "mcpServers": {
        "promptbeacon": {
          "command": "uvx",
          "args": ["--from", "promptbeacon[mcp]>=1.4.0", "promptbeacon", "mcp"]
        }
      }
    }
    ```

    Quit and restart Claude Desktop. It does not read your shell profile, so put keys
    in the file, and keep only the lines for keys you have:

    ```json
    {
      "mcpServers": {
        "promptbeacon": {
          "command": "uvx",
          "args": ["--from", "promptbeacon[mcp]>=1.4.0", "promptbeacon", "mcp"],
          "env": {
            "OPENAI_API_KEY": "sk-your-key",
            "PROMPTBEACON_OPENAI_MODEL": "gpt-6-luna"
          }
        }
      }
    }
    ```

    If the server does not start, replace `uvx` with its full path (`which uvx` on
    macOS and Linux, `where uvx` on Windows). Logs are in `~/Library/Logs/Claude`
    (macOS) or `%APPDATA%\Claude\logs` (Windows).
    Docs: [Connect local MCP servers](https://modelcontextprotocol.io/docs/develop/connect-local-servers).

=== "Cursor"

    [Add to Cursor](cursor://anysphere.cursor-deeplink/mcp/install?name=promptbeacon&config=eyJjb21tYW5kIjoidXZ4IiwiYXJncyI6WyItLWZyb20iLCJwcm9tcHRiZWFjb25bbWNwXT49MS40LjAiLCJwcm9tcHRiZWFjb24iLCJtY3AiXX0=){ .md-button .md-button--primary }

    Or add it to `~/.cursor/mcp.json` (all projects) or `.cursor/mcp.json` (one
    project). `${env:NAME}` reads a variable from Cursor's environment; keep only the
    keys you have:

    ```json
    {
      "mcpServers": {
        "promptbeacon": {
          "command": "uvx",
          "args": ["--from", "promptbeacon[mcp]>=1.4.0", "promptbeacon", "mcp"],
          "env": {
            "OPENAI_API_KEY": "${env:OPENAI_API_KEY}",
            "ANTHROPIC_API_KEY": "${env:ANTHROPIC_API_KEY}"
          }
        }
      }
    }
    ```

    You can also load keys from a file with `"envFile": "${workspaceFolder}/.env"`.
    Docs: [Cursor MCP](https://cursor.com/docs/context/mcp),
    [install links](https://cursor.com/docs/context/mcp/install-links).

=== "VS Code"

    For GitHub Copilot in agent mode.

    [Install in VS Code](vscode:mcp/install?%7B%22name%22%3A%22promptbeacon%22%2C%22type%22%3A%22stdio%22%2C%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22--from%22%2C%22promptbeacon%5Bmcp%5D%3E%3D1.4.0%22%2C%22promptbeacon%22%2C%22mcp%22%5D%7D){ .md-button .md-button--primary }
    [Install in VS Code Insiders](vscode-insiders:mcp/install?%7B%22name%22%3A%22promptbeacon%22%2C%22type%22%3A%22stdio%22%2C%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22--from%22%2C%22promptbeacon%5Bmcp%5D%3E%3D1.4.0%22%2C%22promptbeacon%22%2C%22mcp%22%5D%7D){ .md-button }

    Or from a terminal (adds it to your user profile):

    ```bash
    code --add-mcp '{"name":"promptbeacon","type":"stdio","command":"uvx","args":["--from","promptbeacon[mcp]>=1.4.0","promptbeacon","mcp"]}'
    ```

    For one workspace, create `.vscode/mcp.json`. VS Code can ask for a key once and
    store it securely:

    ```json
    {
      "inputs": [
        {
          "type": "promptString",
          "id": "openai-key",
          "description": "OpenAI API key",
          "password": true
        }
      ],
      "servers": {
        "promptbeacon": {
          "type": "stdio",
          "command": "uvx",
          "args": ["--from", "promptbeacon[mcp]>=1.4.0", "promptbeacon", "mcp"],
          "env": {
            "OPENAI_API_KEY": "${input:openai-key}"
          }
        }
      }
    }
    ```

    Or load a file of keys with `"envFile": "${workspaceFolder}/.env"` in the server
    entry. Docs: [MCP configuration](https://code.visualstudio.com/docs/agents/reference/mcp-configuration),
    [install links](https://code.visualstudio.com/api/extension-guides/ai/mcp).

=== "Windsurf"

    Windsurf is now called Devin Desktop. Open the MCP settings in the app (MCPs under
    Customize, or in the Cascade panel) and open the config file:
    `~/.config/devin/mcp_config.json` for all projects or `.devin/mcp_config.json` for
    one project in Devin Desktop, `~/.codeium/windsurf/mcp_config.json` in earlier
    Windsurf versions. Add:

    ```json
    {
      "mcpServers": {
        "promptbeacon": {
          "command": "uvx",
          "args": ["--from", "promptbeacon[mcp]>=1.4.0", "promptbeacon", "mcp"],
          "env": {
            "OPENAI_API_KEY": "sk-your-key"
          }
        }
      }
    }
    ```

    Leave out `env` for demo mode. Keep keys out of a shared project file: Devin
    Desktop reads personal settings from `.devin/mcp_config.local.json`, which is not
    committed. Refresh the server list after saving.
    Docs: [MCP in Devin Desktop](https://docs.devin.ai/desktop/cascade/mcp),
    [MCP configuration](https://docs.devin.ai/cli/extensibility/mcp/configuration).

=== "Codex CLI"

    Add to `~/.codex/config.toml` (or `.codex/config.toml` in a trusted project).
    `env_vars` forwards the variables that are set in your shell:

    ```toml
    [mcp_servers.promptbeacon]
    command = "uvx"
    args = ["--from", "promptbeacon[mcp]>=1.4.0", "promptbeacon", "mcp"]
    env_vars = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "PROMPTBEACON_OPENAI_MODEL"]
    # The first start downloads PromptBeacon; allow more than the 10 s default.
    startup_timeout_sec = 60
    ```

    Or from a terminal:

    ```bash
    codex mcp add promptbeacon -- uvx --from "promptbeacon[mcp]>=1.4.0" promptbeacon mcp
    ```

    Docs: [Codex MCP](https://learn.chatgpt.com/docs/extend/mcp?surface=cli).

=== "Gemini CLI"

    Add to `~/.gemini/settings.json` (all projects) or `.gemini/settings.json` (one
    project). Gemini CLI hides variables whose names contain `KEY` from servers unless
    you list them in `env`; `$NAME` reads the variable from your shell (an unset one
    becomes empty, which PromptBeacon treats as not configured):

    ```json
    {
      "mcpServers": {
        "promptbeacon": {
          "command": "uvx",
          "args": ["--from", "promptbeacon[mcp]>=1.4.0", "promptbeacon", "mcp"],
          "env": {
            "OPENAI_API_KEY": "$OPENAI_API_KEY",
            "GEMINI_API_KEY": "$GEMINI_API_KEY"
          }
        }
      }
    }
    ```

    Google has moved Gemini CLI users to the Antigravity CLI (`agy`), which reads the
    same `mcpServers` entry from `~/.gemini/config/mcp_config.json`, or from
    `.agents/mcp_config.json` in a workspace. Check with `/mcp`.
    Docs: [Gemini CLI MCP servers](https://geminicli.com/docs/tools/mcp-server/),
    [Antigravity MCP](https://antigravity.google/docs/mcp).

## Keys, models and cost

The server reads the same variables as the CLI, from its environment (the `env` block
of your client's configuration) or a `.env` file in its working directory. Empty values
count as not configured.

| Variable | For |
| --- | --- |
| `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY` (or `GOOGLE_API_KEY`), `MISTRAL_API_KEY`, `COHERE_API_KEY`, `PERPLEXITY_API_KEY` | Real scans with that provider |
| `PROMPTBEACON_<PROVIDER>_MODEL`, e.g. `PROMPTBEACON_ANTHROPIC_MODEL=claude-sonnet-5-5` | A different default model for that provider |
| `PROMPTBEACON_LITELLM_MODEL=ollama/llama3.2` | A local Ollama model: real answers, no key, no cost |
| `TAVILY_API_KEY` | Live web search for the `funnel` tool |
| `GITHUB_TOKEN` | Higher GitHub API limits for `project_scan` |
| `PROMPTBEACON_HOME` | Where the history file lives (default `~/.promptbeacon`) |

You can also just ask for a model ("check with Claude Sonnet", "use my local Ollama
model"): every scanning tool takes a `models` argument such as
`{"anthropic": "claude-sonnet-5-5"}` or `{"litellm": "ollama/llama3.2"}`, and queries
the providers it names. See [Models & local LLMs](models.md).

How cost works:

- **No key:** tools default to keyless demo data. Nothing is billed, and the result has
  a `note` saying it is demo data. Passing `demo: false` without a key is an error, not
  a silent fallback.
- **With keys:** scans are real and billed to your keys. `estimate` prices a scan first
  without sending anything. `max_cost` (US dollars) caps a scan: it is refused when the
  estimate is higher and stops at the cap, and the result then has `partial: true`.
- **Measure once:** pass `save_report` (for example `.promptbeacon/report.json`) to
  `scan` or `project_scan`, then give that file to `compare`, `recommendations`,
  `answers` and `share_assets` as `report_path`. They read it instead of scanning, so
  they cost nothing.
- **Always free:** `providers`, `estimate`, `history`, `answers` and `init_preview`
  never call a paid API.

## Tools

Every tool wraps the Python API and returns compact JSON: no full model responses, only
the short excerpts `answers` returns. Each argument is described in the tool's schema,
which your assistant reads.

| Tool | What it returns | Cost |
| --- | --- | --- |
| `providers` | Which keys are set (never their values), the model each provider will use, whether Tavily is set, and the default mode | Free |
| `estimate` | The expected and upper-bound cost of a scan per model, and whether it fits `max_cost` | Free |
| `scan` | Visibility score, share of voice and rank, presence, a per-brand table, top sources, the models that answered, cost, `partial`, top recommendations, `measurement_tier` | Billed with keys |
| `project_scan` | The same for a project (`github:`, `pypi:`, `npm:`, `crates:`, `hf:`), plus its metadata and the guessed category and competitors, with their basis | Billed with keys |
| `sources` | The domains AI answers cite for the category, and which of them cite the brand (web-grounded by default) | Billed with keys, more than a plain scan |
| `compare` | Each brand side by side: visibility score, mentions, positive share, share of voice, and the brand's rank | Free from a saved report |
| `recommendations` | What to change, with rationale, priority and expected impact, and the explanations of the score; rule-based, or written by an LLM with `smart: true` (one more request) | Free from a saved report |
| `history` | Saved scans over time, the trend, the change since the previous scan, and a significance check of the earlier against the later scans | Free |
| `answers` | The answers behind a saved report, one row each: prompt, provider and model, the tracked brands named (in order), the target's position, list rank and whether it is recommended, a short excerpt and the cited URLs. Filter by `model`, `mentions` or `missing` (a brand named or not); paged with `offset` and `limit` (at most 100) | Free |
| `funnel` | Where the brand drops out of a model of agentic web search: retrieval, rerank or citation | Tavily searches with `TAVILY_API_KEY`; mock backend without |
| `init_preview` | What `promptbeacon init` would write (the weekly workflow, with a diff), the category and competitors it guessed, the cost per run, badge snippets, next steps, and the command to apply it. Never writes files | Free |
| `share_assets` | Writes `badge.svg`, `badge.json`, `card.svg`, `card-dark.svg` (and `card.png`; `rank.svg` and `rank.json` with 2+ competitors) and returns README snippets | Free from a saved report |

`estimate`, `scan` and `project_scan` also let the assistant define the measurement:
`custom_prompts` (the questions your users ask, asked as written; `{category}` is
replaced by the category), `aliases` (other names that count as the brand) and
`stability_runs` (2-20 repeats, reported in a `stability` block with the score per run,
its confidence interval and the prompts that flip-flop). Pass the same values to
`estimate` first: custom prompts and runs change the price.

A scan without a category returns a `warning` that the prompts were generic. Results
with `measurement_tier: "demo"` are canned data, not a measurement.

Real scans made by `scan` and `project_scan` are saved to the local history
(`save_history: false` skips it), the same file `promptbeacon history` reads. Under the
Claude Code plugin, the history lives in the plugin's data directory; pass `history` a
`storage` path to read the CLI's `~/.promptbeacon/data.db` instead.

## Skills

The plugin includes four skills. They are plain `SKILL.md` files in
[`plugins/promptbeacon/skills`](https://github.com/yotambraun/promptbeacon/tree/main/plugins/promptbeacon/skills),
so an agent that supports skills can use them, and any agent can follow them as
instructions.

| Skill | What it does |
| --- | --- |
| `ai-visibility-review` | A full review: checks keys, prices the scan and asks before spending, scans once, then compares, reads the answers behind the numbers, checks sources, history and significance, and ends with evidence and next steps |
| `ai-visibility` | A quick check: score, share of voice and how it was measured |
| `share-card` | A README badge, shields.io JSON and light and dark share cards |
| `visibility-ci` | A weekly or pull-request GitHub workflow (`/promptbeacon:visibility-ci` in Claude Code) |

## Troubleshooting

- **The server does not start.** Run the command above in a terminal: it should wait
  silently for input (stop it with Ctrl+C). Desktop apps may not find `uvx` on their
  `PATH`; use its full path as the `command`.
- **The first start is slow or times out.** The first run downloads PromptBeacon and
  its dependencies; later starts use uv's cache. Raise the client's startup timeout
  (Codex: `startup_timeout_sec`).
- **Results say demo although you set a key.** Ask the assistant to call `providers`.
  The key has to reach the server's environment: desktop apps don't read your shell
  profile, so set it in the client's `env` block.
- **Only the older tools appear.** Keep `>=1.4.0` in the command, so uv doesn't reuse a
  cached older release.

The server writes nothing to stdout except the protocol.
