# AI Recommendation Index

!!! note "Coming soon: no results are published yet"
    The Index is built and tested, but it has not been run against real models. There
    are no rankings yet, and nothing on this page is one.

A monthly, public index of which open-source projects AI assistants recommend, in 30
developer categories such as "python http client", "vector database", "javascript test
runner" and "static site generator".

## How it will work

- **Fixed questions.** Each category has a pinned protocol: ten developer prompts
  ("What is the best python http client?", "Which python http client should I use for a
  new project?", ...), the same models (OpenAI gpt-6-luna, Anthropic claude-haiku-5-5,
  Google gemini-3.5-flash-lite), three runs of every prompt, fixed temperature and
  token limit. 90 answers per category, 2,700 per monthly run.
- **Counted, not judged.** Each answer is checked for whole-word mentions of the
  category's candidate projects (4 to 9 per category, listed alphabetically). Projects
  are ranked by mention rate only, with a 95% confidence interval; when two intervals
  overlap the page says the order is not statistically clear.
- **Everything published.** Each category page links its JSON snapshot, every raw answer
  and the protocol (with its SHA-256), so anyone can check or reproduce a number.
- **Honest tier.** Answers come from the models' APIs without web search ("base
  model"), which reflects training memory and approximates, but does not equal, what
  the consumer apps show.
- **A badge for maintainers.** Each project gets a rank badge such as `AI rank | #2 of
  7 · python http clients`, the same variant `promptbeacon badge --metric rank` makes for
  your own scans (see [Badges & share cards](share.md#rank-in-your-category)).

## Requests and disputes

Requests for a new category or project, and disputes about a result, will go through
public GitHub issues with the `index` label. Changes take effect in the next run;
published snapshots are never edited.

## Measure your own project now

You do not need to wait for the Index:

```bash
promptbeacon scan --repo owner/name                 # or --pypi, --npm, --crate, --hf
promptbeacon init                                   # weekly workflow + badge
promptbeacon badge --report report.json --metric rank   # your rank among the projects you name
```

The generator, the 30 protocols and a labelled demo build (with placeholder project
names) are in the repository's
[`index/` folder](https://github.com/yotambraun/promptbeacon/tree/main/index).
