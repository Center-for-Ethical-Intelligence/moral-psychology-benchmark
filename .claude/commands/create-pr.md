# Create a Pull Request

Create a PR for the current branch against the org repo.

## Arguments
- $ARGUMENTS: Optional PR title or description

## Instructions

1. Check if GitHub CLI (`gh`) is installed:
   ```bash
   gh --version
   ```
   If not installed, install it:
   ```bash
   brew install gh
   gh auth login
   ```

2. Check git status and ensure all changes are committed
3. Push the current branch:
   ```bash
   git push -u origin $(git branch --show-current)
   ```
4. Create the PR:
   ```bash
   gh pr create --repo Center-for-Ethical-Intelligence/moral-psychology-benchmark --base main --title "<title>" --body "<body>"
   ```
   - If `$ARGUMENTS` provided, use it as the title
   - Generate a summary body from `git diff main...HEAD`
   - Include a test plan
5. Ask the user who to add as reviewers (Erik: `nordbyerik`, Jenny: `hanzhenzhujene`, Joseph: `sunyuding`)
6. Add reviewers:
   ```bash
   gh pr edit <PR_NUMBER> --repo Center-for-Ethical-Intelligence/moral-psychology-benchmark --add-reviewer <usernames>
   ```
7. Report the PR URL
