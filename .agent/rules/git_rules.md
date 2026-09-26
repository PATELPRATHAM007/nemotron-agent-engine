# Git & Version Control Protocol

1. **Commit Messages**: Follow Conventional Commits format: `<type>(<scope>): <short description>`.
2. **Autonomous Rollback**: If an agent fails verification after 3 debug attempts, all modifications MUST be reverted via `git checkout` or `git stash`.
3. **Atomic Changes**: Each mission should result in one cohesive, self-contained changeset.
