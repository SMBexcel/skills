# SMBexcel Skills

Open-source Claude skills built and maintained by [SMBexcel](https://www.smbexcel.com).

Each skill is a self-contained folder you drop into your Claude skills directory. No build step, no install script — markdown all the way down.

---

## Catalog

| Skill | Version | What it does |
|---|---|---|
| [lemonade](./lemonade) | `1.2` | Plug-and-play persistent memory for Claude chats. Distill / rehydrate via a Notion database you own. Counters context rot. |
| [dealstream-deals](./dealstream-deals) | `1.0` | Get filtered Dealstream listings into a CSV via your logged-out browser session. Guided flow with legal-posture briefing. Built for SMB searchers sourcing their own deal flow. **Claude Code only.** |
| [ibba-broker-emails](./ibba-broker-emails) | `1.0` | Get every IBBA business broker (~2,800) into a CSV — name, company, email, phone, website, location — from the directory's own public endpoints. No login, no cookie, no paid tool. Legal-posture briefing included. **Claude Code only.** |

More shipping soon — see the [SMBexcel newsletter](https://www.smbexcel.com) for what's next.

---

## Installing a skill

Each skill folder has its own `README.md` with skill-specific setup, but the general pattern:

### Option 1 — Download a release (recommended for non-developers)

1. Open the [Releases page](https://github.com/SMBexcel/skills/releases) and grab the zip for the skill + version you want (e.g. `lemonade-v1.2.zip`).
2. Unzip — you'll get a folder like `lemonade/` containing `SKILL.md` and `references/`.
3. Drop the folder into your Claude skills directory:
   - **Claude Code** (CLI): `~/.claude/skills/<skill-name>/`
   - **claude.ai** (Cowork mode): install via the Skills UI
4. Open the skill's `README.md` for any one-time setup (connectors, config, etc.).

### Option 2 — Clone the whole repo

```bash
git clone https://github.com/SMBexcel/skills.git
cp -R skills/lemonade ~/.claude/skills/
```

Then follow the per-skill README.

---

## Requirements

Requirements vary by skill — some need MCP connectors (e.g. lemonade needs Notion), some run only in Claude Code with a shell (e.g. dealstream-deals needs `bash`, `curl`, `python3`). Each skill's README lists exactly what it needs.

---

## Versioning

- Skills follow semver-ish: `MAJOR.MINOR` (e.g. `1.2`).
- Each version is tagged and released as a downloadable zip on the [Releases page](https://github.com/SMBexcel/skills/releases).
- Breaking changes bump MAJOR; behavior-additive changes bump MINOR. The skill's own `SKILL.md` always carries its `Version:` field and a changelog at the bottom.

---

## Contributing

Issues and pull requests welcome — file under the relevant skill folder. Bug reports especially helpful; if you hit something weird in your own setup, open an issue.

---

## License

MIT, unless a specific skill folder overrides it. See [LICENSE](./LICENSE).

---

## More

- Newsletter: [www.smbexcel.com](https://www.smbexcel.com)
- Organization: [github.com/SMBexcel](https://github.com/SMBexcel)
- Author: David Schreiber
