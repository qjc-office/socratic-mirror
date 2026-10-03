# socratic-mirror

[한국어](README.md)

A Claude Code plugin that finds one premise you keep assuming, without evidence, across your past conversations with Claude, and questions it. No advice, no comfort. When you admit the premise is wrong, it says `Aporia.` and stops.

```
> /socrates
This tool asks questions only, without comfort. Type `stop` anytime to end.
You keep assuming "customers only care about price".
  "they'll just pick the cheapest" (2026-09-02) / "price is the only lever" (2026-09-18)
Why did your most expensive client renew twice?
> ...they were happy with the support.
```

(The exchange above is a made-up example.)

## Install

Run these two lines in Claude Code:

```
/plugin marketplace add qjc-office/socratic-mirror
/plugin install socratic-mirror
```

Requires Python 3.9 or later (preinstalled on macOS).

## Usage

| Command | What it does |
|---|---|
| `/socrates` | Picks one premise from the last 30 days of this project's conversations and questions it |
| `/socrates triad` | Alternates three lenses: Socrates (counter-examples), Confucius (rectification of names: does your role match what you did?), Buddha (dependent origination: trace the first contact behind the attachment). Declares `Triple aporia.` only when all three land on the same point |
| `/socrates close` | Wraps up with three lines (what you had wrong, the question you should have been answering, one change for today) plus three actions for this week, and saves them to the log |
| `--days N` | Change the time window (default 30) |
| `--all-projects` | Use conversations from every project |

"This project" means the whole git repository when you are inside one, otherwise conversations started in the current folder. Type `stop` anytime.

## Privacy

- Your history (`~/.claude/projects`) is read locally. The plugin itself makes no network calls.
- The extracted utterances are sent to the model provider (Anthropic) like any other conversation, the same as pasting them into Claude yourself.
- Strings that look like API keys are masked first, but no masking catches every secret.
- The session log lives at `~/.socratic-mirror/log.md` and the extract cache at `~/.socratic-mirror/cache/extract.txt`, both readable only by you (mode 600). Delete `~/.socratic-mirror` to remove them.

## Safety

A questions-only tool is not for hard days. If the conversation shows signs of crisis, it stops interrogating and points you to support (in Korea, 109; elsewhere, your local emergency number or crisis line). It is not a substitute for counseling or therapy.

## Attribution

The interrogation prompts were adapted from prompts shared on social media.

## Known limits

- Claude Code's history format is not a public spec and may change. If history exists but nothing can be extracted, the plugin says so and stops (exit code 3). Please open an issue.
- Logs or code you pasted are counted as your own words. The analysis step filters them, imperfectly.

## Development

```
python3 -m pytest              # unit tests
bash scripts/run-evals.sh      # behaviour evals (run from a normal terminal, outside Claude Code)
```

## License

MIT
