# AGENTS.md

- 한국어로 응답해.

## Worktree Location

Worktrees must be created **outside** the project directory, under the parent `coding-workspace` path.

**Pattern:** `/home/chowon442/coding-workspace/.worktrees/{project-name}/{worktree-name}`

**Example:**
```
/home/chowon442/coding-workspace/.worktrees/manim-video-gen/worktree-task-01
```

**Steps:**
1. Create parent dir: `mkdir -p /home/chowon442/coding-workspace/.worktrees/{project-name}`
2. Add to `.gitignore` of the **parent** workspace if needed
3. `git worktree add <path> -b <branch-name>`

## Branch Naming

**During development:** Use simple names like `worktree-task-02`

**Before PR:** Rename branch to `type/issue-number-brief-description` format:
```bash
git branch -m worktree-task-02 feat/1.02-short-extract
```

Types: `feat`, `fix`, `refactor`, `chore`, `docs`, `test`
