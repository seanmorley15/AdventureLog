# Contributing to AdventureLog

Thank you for your interest in contributing to **AdventureLog**!
AdventureLog is an open-source project built by and for people who love travel, exploration, and self-hosting. Contributions of all kinds are welcome — whether that’s fixing bugs, improving documentation, suggesting features, or writing code.

Our goal is to keep the project **open, welcoming, and organized** so that contributors can collaborate effectively and the codebase remains maintainable long-term.

This document explains how to contribute and the workflow we use.

---

# How Contributions Work

AdventureLog uses a structured workflow to keep development organized and to make it easier for contributors to collaborate.

All development follows this process:

```
Issue → Discussion → Approved → Ready → Development → Review → Merge
```

### 1. Open or Find an Issue

Before starting work, **please open an issue or find an existing one**.

Issues allow us to:

- discuss ideas before development begins
- coordinate work between contributors
- prevent duplicate efforts
- maintain a clear roadmap for the project

If you have an idea for a new feature or improvement, feel free to open an issue describing it.

---

### 2. Wait for Approval / Ready Status

Issues move through several stages:

**Backlog**
An idea or request that has not yet been reviewed.

**Needs Discussion**
The idea requires maintainer feedback or design discussion.

**Approved**
The concept has been accepted but may require planning.

**Ready**
The issue is ready for contributors to begin working on it.

⚠️ **Pull Requests should only be opened for issues marked `Ready`.**

This helps ensure contributors work on changes that are aligned with the project’s roadmap.

---

### 3. Start Working on the Issue

Once an issue is marked **Ready**, you can begin working on it.

If you plan to work on a larger issue, feel free to comment on the issue to let others know.

This helps prevent duplicate work.

---

### 4. Create a Pull Request

When your changes are ready, open a pull request targeting the **`development` branch**.

Your pull request must include a reference to the issue it resolves:

```
Closes #issue-number
```

This allows the project automation to track progress and update the project board.

Example PR description:

```
Closes #123

Adds support for exporting trips as GPX files.
```

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

After approval, your pull request will be merged into the **`development` branch**.

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

# Documentation Changes

If your changes affect:

- user workflows
- environment variables
- deployment setup
- API behavior
- configuration

please update the documentation in the:

```
/docs
```

folder accordingly.

Keeping documentation accurate is extremely important.

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

## Our Pledge

At AdventureLog, we are committed to creating a community that fosters adventure, exploration, and innovation.

We welcome contributors of all experience levels and backgrounds. Everyone should feel comfortable participating and sharing ideas.

---

## Our Standards

To maintain a positive environment, we encourage the following behaviors:

- **Inclusivity** — Use welcoming and inclusive language.
- **Respect** — Respect differing viewpoints and experiences.
- **Constructive Feedback** — Provide helpful and actionable feedback.
- **Collaboration** — Work together to improve the project.

Examples of unacceptable behavior include:

- Personal attacks or harassment
- Discriminatory language
- Spamming or promotional misuse of project spaces
- Sharing private information without consent

---

## Maintainer Responsibilities

The AdventureLog maintainers are responsible for enforcing this Code of Conduct and maintaining a respectful community.

If necessary, maintainers may:

- moderate comments
- close pull requests
- remove contributions
- restrict participation

These actions will only be taken when necessary to protect the community and the project.

---

## Scope

This Code of Conduct applies to all spaces related to AdventureLog, including:

- GitHub repositories
- GitHub Discussions
- documentation
- social media
- community spaces

---

## Reporting Issues

If you experience or witness unacceptable behavior, please contact the maintainers at:

```
contact@adventurelog.app
```

All reports will be handled confidentially.

---

## Attribution

This Code of Conduct is inspired by the
Contributor Covenant (v1.4) and adapted for the AdventureLog community.
