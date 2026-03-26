## 📝 Description

**Why is this change needed?**
* [Add your explanation here...]

**What does this PR do?**
* _[e.g., Implemented 6-second politeness window decorator.]_
* _[e.g., Added TF-IDF scoring logic to the indexer.]_
* [Add your specific changes here...]

## 🔗 Related Issue(s)

Closes #

---

## 🏷️ Type of Change

- [ ] 🐛 **Bug fix** (`fix:`)
- [ ] 🚀 **New feature** (`feat:`)
- [ ] 🧹 **Chore/Refactor** (`chore:` or `refactor:`)
- [ ] 📝 **Documentation update** (`docs:`)
- [ ] 🧪 **Test addition/update** (`test:`)

---

## ✅ Quality Assurance Checklist

**Code Standards & Constraints:**
- [ ] **Conventional Commits:** PR title strictly follows `<type>: <description>`.
- [ ] **Feature Branching:** PR branch follows `<type>/<issue-number>/<short-description>`.
- [ ] **Pre-commit:** I have run `uv run pre-commit run --all-files` (Ruff/Mypy passed).
- [ ] **Politeness Window:** If crawler logic was modified, the strict 6-second delay is enforced.
- [ ] **Type Hints:** All new functions and methods include strict Python type hints.

**Testing & Coverage:**
- [ ] **Pytest:** I have added/updated unit or integration tests for these changes.
- [ ] **Mocking:** Outbound HTTP requests are mocked; tests do not hit live servers.
- [ ] **Codecov:** Coverage meets the **80% threshold** (check PR comment).
- [ ] **Test Analytics:** No new flaky tests or performance regressions introduced.

**Documentation:**
- [ ] **README / Wiki:** Setup instructions and CLI usage examples have been updated if necessary.

---

## 📊 Coverage & Analytics (Codecov)

| Metric             | Status                                                                         |
| :----------------- | :----------------------------------------------------------------------------- |
| **Total Coverage** | % (Check PR Comment)                                                           |
| **Test Analytics** | [View Failures/Flakes](https://app.codecov.io/gh/scAB1001/search-engine-tool/) |

---

## 📸 Proof of Work

<details>
<summary><b>💻 CLI Execution Output</b> (Click to expand)</summary>

```bash
# Paste the terminal output of your new command here
# e.g., output from `uv run search-engine find "Einstein"`

```

</details>

<details>
<summary><b>🧪 Pytest Coverage & Results</b> (Click to expand)</summary>

```bash
# Paste summary from pytest-output.txt or coverage report

```

</details>

-----

## 📦 CI/CD Artifacts

  - [ ] **Consolidated Results:** `all-ci-results.zip` (Check the "Actions" tab)

## 💬 Additional Notes for Reviewer

  * [Add any specific areas you want the reviewer to look at, or known technical debt left behind...]
