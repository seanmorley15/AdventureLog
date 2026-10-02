# Contributing to AdventureLog

Thank you for your interest in contributing to **AdventureLog**!
AdventureLog is an open-source project built by and for people who love travel, exploration, and self-hosting. Contributions of all kinds are welcome — whether that’s fixing bugs, improving documentation, suggesting features, or writing code.

Our goal is to keep the project **open, welcoming, and organized** so that contributors can collaborate effectively and the codebase remains maintainable long-term.

This document explains how to contribute and the workflow we use.

Please also read our [Code of Conduct](CODE_OF_CONDUCT.md).

---

# How Contributions Work

AdventureLog uses two contribution lanes so small fixes land quickly while larger changes stay aligned with the roadmap.

```
Bug fix / docs / translations  →  Pull request  →  Review  →  Merge

Feature / behavior change  →  Issue  →  Ready  →  Pull request  →  Review  →  Merge
```

You can open a feature pull request early (including as a draft). Merge waits until the linked issue is labeled `ready` or `in progress`.

### 1. Open or Find an Issue

**Bug fixes, documentation, and translations** do not require an issue. Opening one is still useful for tracking, and you can link it with `Closes #N`.

**Features and other behavior changes** should have an issue so maintainers can discuss scope before merge. Feel free to open the issue and a draft pull request together.

Issues allow us to:

- discuss ideas before development begins
- coordinate work between contributors
- prevent duplicate efforts
- maintain a clear roadmap for the project

---

### 2. Issue Status Labels

Issues move through several stages:

**Backlog**
An idea or request that has not yet been reviewed.

**Needs Discussion**
The idea requires maintainer feedback or design discussion.

**Approved**
The direction has been accepted and will be done, but not right now. Contributors should not start work yet.

**Ready**
The issue is open for contributors. A feature pull request linked to this issue can merge.

**In progress**
Someone is actively working on it (often set automatically when a qualifying pull request opens).

---

### 3. Start Working

Comment on larger issues to let others know you are taking them.

For features, you can start coding before the issue is ready. Keep the pull request as a draft until a maintainer adds `ready`.

---

### 4. Create a Pull Request

Open pull requests against the **`development`** branch.

**Fast lane** — check **Bug fix** or **Documentation update** in the pull request template. These do not need a Ready issue. Documentation-only and locale-only changes are also detected automatically.

**Feature lane** — check **New feature**, **Refactor**, **Performance**, or **Other**, and link an issue:

```
Closes #123
```

Example:

```
Closes #123

Adds support for exporting trips as GPX files.
```

The contribution check (`contribution-policy`) stays on the pull request. It does not close the PR. When the linked issue is labeled `ready` or `in progress`, the check updates automatically.

---

### 5. Review Process

Once submitted, maintainers will review your pull request.

Reviews may include:

- code quality improvements
- consistency with the existing architecture
- performance considerations
- documentation updates

Please be open to feedback — reviews are intended to **improve the project and help contributors grow**.

---

### 6. Merge

After approval, your pull request will be merged into the **`development`** branch.

From there, it will eventually be included in the next release.

Thank you for helping improve AdventureLog!

---

# AI / LLM Assistance

Using AI tools (such as ChatGPT, Copilot, or other LLMs) **is allowed** when contributing to AdventureLog.

However, contributors are responsible for ensuring that generated code:

- is **correct and fully understood**
- follows the **project’s coding standards**
- integrates properly with the existing architecture
- does not introduce unnecessary complexity

AI-generated code that does not meet these standards may be rejected or the pull request may be closed.

Please review and clean up any AI-generated code before submitting it.

---

# Code Quality Expectations

To keep the project maintainable, all contributions should:

- follow the existing **code structure and architecture**
- use clear and readable code
- avoid unnecessary dependencies
- include documentation updates when relevant
- maintain compatibility with the existing system

AdventureLog currently includes:

- **Django** for the backend
- **SvelteKit** for the frontend
- **Docker-based deployments**

When contributing, please try to match the **style and patterns already used in the project**.

---

# Testing

Frontend changes that add or change a user flow should come with a Playwright spec under `frontend/tests/e2e`. The [testing guide](documentation/docs/install/testing.md) covers running the suite locally; it also runs in CI on every pull request.

---

# Documentation Changes

If your changes affect:

- user workflows
- environment variables
- deployment setup
- API behavior
- configuration

please update the documentation in the:

```
documentation/
```

folder accordingly.

Keeping documentation accurate is extremely important. Documentation-only pull requests do not need a Ready issue.

---

# Good Issues for New Contributors

If you are new to the project, look for issues labeled:

```
good first issue
help wanted
```

These are great starting points for new contributors.

---

# Code of Conduct

Everyone participating in AdventureLog is expected to follow our [Code of Conduct](CODE_OF_CONDUCT.md).

Reports can be sent confidentially to `contact@adventurelog.app`.

---

# Maintainer note: required status check

To enforce the feature lane on merge, the GitHub ruleset (or branch protection) for **`development`** must require the status check named **`contribution-policy`**. Without that setting, a failing check is visible on the pull request but does not block merge. Maintainer and Dependabot pull requests remain exempt in the workflow.
