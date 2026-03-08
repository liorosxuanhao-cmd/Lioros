# CLAUDE.md — AI Assistant Guide for Lioros

This file provides context and conventions for AI assistants (Claude Code and similar tools) working in this repository.

---

## Repository Overview

| Field | Value |
|---|---|
| **Name** | Lioros |
| **Owner** | liorosxuanhao-cmd |
| **Status** | Early initialization — stub repository |
| **Primary Language** | Not yet determined |
| **Remote** | `http://local_proxy@127.0.0.1:55451/git/liorosxuanhao-cmd/Lioros` |

The repository was initialized with a single `README.md` placeholder. No source code, dependencies, build system, or test infrastructure has been set up yet. This file should be updated as the project grows.

---

## Repository Structure

```
Lioros/
├── README.md       # Project description placeholder
└── CLAUDE.md       # This file — AI assistant guide
```

As the project evolves, update this tree to reflect the actual layout.

---

## Git Conventions

### Branch Naming

- `main` / `master` — stable, production-ready code
- `claude/<description>-<id>` — branches created or managed by Claude Code (e.g., `claude/add-claude-documentation-fPh9q`)
- `feat/<description>` — new features
- `fix/<description>` — bug fixes
- `chore/<description>` — maintenance tasks (deps, docs, tooling)

### Commit Messages

Use the imperative mood and keep the subject line under 72 characters:

```
Add user authentication module
Fix null pointer in payment handler
Update README with setup instructions
```

Optionally follow with a blank line and a longer body explaining **why** (not what).

### Push Workflow

Always push with tracking set:

```bash
git push -u origin <branch-name>
```

For Claude-managed branches the branch name must start with `claude/` and end with the matching session ID, otherwise the push will be rejected with HTTP 403.

---

## Development Workflow (to be defined)

Once a tech stack is chosen, document the following here:

1. **Install dependencies** — e.g., `npm install` / `pip install -r requirements.txt`
2. **Run in development mode** — e.g., `npm run dev`
3. **Build for production** — e.g., `npm run build`
4. **Run tests** — e.g., `npm test` / `pytest`
5. **Lint / format** — e.g., `npm run lint` / `ruff check .`

---

## Testing

No test framework has been configured yet. When tests are added:

- Place tests adjacent to source files or in a top-level `tests/` / `__tests__/` directory.
- Ensure all tests pass before opening a pull request.
- Do not disable or skip tests to make CI pass — fix the underlying issue instead.

---

## Code Style Conventions

No linting or formatting configuration exists yet. When tooling is added, document it here. In the meantime, follow these general principles:

- Prefer clarity over cleverness.
- Keep functions small and single-purpose.
- Name variables and functions descriptively in English.
- Avoid committing commented-out code or debug statements.
- Add comments only where the logic is non-obvious.

---

## Configuration & Secrets

- Never commit secrets, API keys, passwords, or tokens.
- Use environment variables loaded from a `.env` file (gitignored).
- Provide a `.env.example` with placeholder values so others know what variables are required.

---

## AI Assistant Instructions

When working in this repository, Claude Code and other AI assistants should:

1. **Read this file first** before making any changes to understand the current project state.
2. **Update this file** whenever the project structure, conventions, or workflows change significantly.
3. **Work on the correct branch** — see the branch specified in any issue or task description. Branches starting with `claude/` are managed by Claude Code.
4. **Commit incrementally** with clear messages rather than one large catch-all commit.
5. **Never force-push** to `main` or `master`.
6. **Never skip hooks** (`--no-verify`) unless the user explicitly requests it.
7. **Ask before deleting** files, branches, or data that may represent in-progress work.
8. **Keep changes minimal** — only touch what is needed to complete the task. Avoid unrelated refactors, style cleanups, or feature additions.
9. **Do not add comments, docstrings, or type annotations** to code that was not changed as part of the task.
10. **Prefer editing existing files** over creating new ones.

---

## Updating This File

This `CLAUDE.md` should be kept current. Update it when:

- A language, framework, or major library is added or removed.
- The directory structure changes significantly.
- New development, testing, or deployment workflows are introduced.
- Coding or git conventions are decided upon or changed.

Last updated: 2026-03-08
