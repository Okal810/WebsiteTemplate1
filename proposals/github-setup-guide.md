# GitHub Setup & Issue Templates

This guide provides ready-to-use commands and templates for setting up your GitHub repository with all the optimization issues.

## Quick GitHub CLI Setup

If you have GitHub CLI installed, you can create all labels and milestones quickly:

```bash
# Install GitHub CLI if needed
# macOS: brew install gh
# Windows: winget install GitHub.cli
# Linux: See https://cli.github.com

# Login
gh auth login

# Navigate to your repo
cd /path/to/server-systems
```

## Step 1: Create Labels

```bash
# Priority Labels
gh label create "priority:high" --color "d73a4a" --description "Critical issues that should be addressed ASAP"
gh label create "priority:medium" --color "fb8c00" --description "Important improvements"
gh label create "priority:low" --color "fbca04" --description "Nice-to-have enhancements"

# Category Labels
gh label create "security" --color "d73a4a" --description "Security-related improvements"
gh label create "performance" --color "0e8a16" --description "Performance optimizations"
gh label create "code-quality" --color "0052cc" --description "Code maintainability improvements"
gh label create "testing" --color "5319e7" --description "Testing infrastructure"
gh label create "monitoring" --color "006b75" --description "Observability and monitoring"
gh label create "infrastructure" --color "8b4513" --description "Deployment and infrastructure"
gh label create "documentation" --color "808080" --description "Documentation updates"
gh label create "enhancement" --color "84b6eb" --description "New features or improvements"
gh label create "database" --color "0052cc" --description "Database-related"
gh label create "automation" --color "fb8c00" --description "Automation improvements"
gh label create "observability" --color "006b75" --description "Logging and monitoring"

# Additional Labels
gh label create "good-first-issue" --color "7057ff" --description "Good for newcomers"
gh label create "help-wanted" --color "008672" --description "Extra attention needed"
gh label create "technical-debt" --color "333333" --description "Technical debt to address"
```

## Step 2: Create Milestones

```bash
# Calculate dates (adjust as needed)
# Format: YYYY-MM-DD

gh api repos/:owner/:repo/milestones -f title="v2.9.0 - Security Hardening" -f description="Production-ready security features" -f due_on="2025-02-14T00:00:00Z"

gh api repos/:owner/:repo/milestones -f title="v3.0.0 - Performance Optimization" -f description="2x performance improvement" -f due_on="2025-03-01T00:00:00Z"

gh api repos/:owner/:repo/milestones -f title="v3.1.0 - Testing & Quality" -f description="80%+ test coverage, clean architecture" -f due_on="2025-03-15T00:00:00Z"

gh api repos/:owner/:repo/milestones -f title="v3.2.0 - Production Infrastructure" -f description="Docker deployment, CI/CD, monitoring" -f due_on="2025-03-30T00:00:00Z"

gh api repos/:owner/:repo/milestones -f title="v3.3.0 - Polish & Documentation" -f description="Complete documentation, full observability" -f due_on="2025-04-15T00:00:00Z"
```

## Step 3: Create Issue Templates

Create `.github/ISSUE_TEMPLATE/` directory with templates:

### Security Issue Template
```markdown
<!-- .github/ISSUE_TEMPLATE/security.md -->
---
name: Security Enhancement
about: Security-related improvements
title: '[SECURITY] '
labels: security, enhancement
assignees: ''
---

## Security Concern
<!-- Describe the security aspect being addressed -->

## Current Implementation
<!-- How it works now -->
```python
# Code example
```

## Proposed Solution
<!-- What should be implemented -->

## Implementation Tasks
- [ ] Task 1
- [ ] Task 2
- [ ] Task 3
- [ ] Test security improvement
- [ ] Update documentation

## Security Impact
<!-- High/Medium/Low - How this improves security -->

## Estimated Effort
<!-- Hours needed -->
```

### Performance Issue Template
```markdown
<!-- .github/ISSUE_TEMPLATE/performance.md -->
---
name: Performance Optimization
about: Performance-related improvements
title: '[PERF] '
labels: performance, enhancement
assignees: ''
---

## Performance Issue
<!-- What is slow or inefficient? -->

## Current Metrics
<!-- Benchmark data if available -->

## Proposed Optimization
<!-- How to improve it -->

## Implementation Tasks
- [ ] Task 1
- [ ] Task 2
- [ ] Benchmark before/after
- [ ] Update documentation

## Expected Impact
<!-- Response time improvement, resource usage, etc. -->

## Estimated Effort
<!-- Hours needed -->
```

## Step 4: Create Issues from Files

You can create issues directly from the prepared markdown files:

```bash
# Example: Create Issue #1
gh issue create \
  --title "Enable Secure Cookie Flag for Production" \
  --label "security,priority:high,enhancement" \
  --milestone "v2.9.0 - Security Hardening" \
  --body "$(cat <<'EOF'
**Description:**
Currently, the \`secure\` flag is set to \`False\` for admin session cookies, which means cookies can be transmitted over unencrypted HTTP connections. This should be enabled for production environments using HTTPS.

**Current Implementation:**
\`\`\`python
# app/routes/admin.py, line ~30
response.set_cookie(
    'admin_session_token', token,
    path='/', httponly=True, samesite='Lax', 
    secure=False,  # ← Currently disabled
    max_age=1800
)
\`\`\`

**Tasks:**
- [ ] Add environment detection (DEV vs PROD)
- [ ] Set \`secure=True\` when running with HTTPS
- [ ] Update config.py with \`SECURE_COOKIES\` flag
- [ ] Test with nginx/reverse proxy setup
- [ ] Document in deployment guide

**Estimated Effort:** 1-2 hours

**Security Impact:** Medium - Prevents cookie interception in production
EOF
)"
```

### Batch Create Script

Create a script to create all issues:

```bash
#!/bin/bash
# create_all_issues.sh

# Read from the detailed issue files and create each one
# This is a template - you'll need to parse the markdown files

create_issue() {
    local title="$1"
    local labels="$2"
    local milestone="$3"
    local body="$4"
    
    gh issue create \
        --title "$title" \
        --label "$labels" \
        --milestone "$milestone" \
        --body "$body"
}

# Example: Issue #1
create_issue \
    "Enable Secure Cookie Flag for Production" \
    "security,priority:high,enhancement" \
    "v2.9.0 - Security Hardening" \
    "See github-issues-security.md - Issue 1"

# Repeat for all 29 issues...
```

## Step 5: Create Project Board

```bash
# Create a new project
gh project create --title "Server Systems Optimization" --body "Track all optimization issues"

# Or use the web interface:
# 1. Go to Projects tab
# 2. Click "New project"
# 3. Choose "Table" template
# 4. Name it "Server Systems Optimization"
```

### Project Board Setup

**Columns to create:**
1. 📋 Backlog - Issues not yet started
2. 📝 To Do - Ready to be worked on
3. 🚧 In Progress - Currently being worked on
4. 👀 Review - In code review
5. ✅ Done - Completed

**Custom Fields to add:**
- **Priority:** Single select (High, Medium, Low)
- **Effort (hours):** Number
- **Category:** Single select (Security, Performance, Code Quality, Testing, Infrastructure)
- **Assignee:** Person
- **Sprint:** Iteration

## Step 6: Automation Setup

Create workflow files for automation:

```yaml
# .github/workflows/issue-automation.yml
name: Issue Automation

on:
  issues:
    types: [opened, labeled]

jobs:
  auto-assign-milestone:
    runs-on: ubuntu-latest
    steps:
      - name: Assign to milestone based on labels
        uses: actions/github-script@v6
        with:
          script: |
            const issue = context.payload.issue;
            const labels = issue.labels.map(l => l.name);
            
            let milestone;
            if (labels.includes('security')) {
              milestone = 'v2.9.0 - Security Hardening';
            } else if (labels.includes('performance')) {
              milestone = 'v3.0.0 - Performance Optimization';
            } else if (labels.includes('code-quality')) {
              milestone = 'v3.1.0 - Testing & Quality';
            } else if (labels.includes('infrastructure')) {
              milestone = 'v3.2.0 - Production Infrastructure';
            }
            
            if (milestone) {
              const milestones = await github.rest.issues.listMilestones({
                owner: context.repo.owner,
                repo: context.repo.repo,
              });
              
              const targetMilestone = milestones.data.find(m => m.title === milestone);
              
              if (targetMilestone) {
                await github.rest.issues.update({
                  owner: context.repo.owner,
                  repo: context.repo.repo,
                  issue_number: issue.number,
                  milestone: targetMilestone.number,
                });
              }
            }
```

## Manual Issue Creation (Web Interface)

If you prefer to create issues manually through GitHub's web interface:

1. Go to your repository
2. Click "Issues" tab
3. Click "New issue"
4. For each issue:
   - **Title:** Copy from issue files
   - **Description:** Copy full issue body
   - **Labels:** Add appropriate labels
   - **Milestone:** Assign to correct milestone
   - **Assignees:** Assign to yourself or team members
   - **Projects:** Add to project board
5. Submit issue

## Issue Numbering

The issues are numbered 1-29 in the documentation. GitHub will auto-number them based on creation order. To maintain consistency:

1. Create issues in numerical order
2. Or, reference them by descriptive name in PRs
3. Or, create a mapping document

## Tips for Issue Management

### Priority Management
```bash
# View high priority issues
gh issue list --label "priority:high"

# View issues by milestone
gh issue list --milestone "v2.9.0 - Security Hardening"

# View your assigned issues
gh issue list --assignee "@me"
```

### Bulk Operations
```bash
# Close all issues in a milestone (when complete)
gh issue list --milestone "v2.9.0 - Security Hardening" --json number --jq '.[].number' | xargs -I {} gh issue close {}

# Add label to multiple issues
gh issue list --search "security" --json number --jq '.[].number' | xargs -I {} gh issue edit {} --add-label "high-priority"
```

### Creating from Templates
```bash
# Create issue from template
gh issue create --template security.md

# Or interactively
gh issue create
# Then select template from menu
```

## Next Steps After Setup

1. **Review all created issues** - Adjust priorities and assignments
2. **Create initial project board view** - Organize by priority
3. **Set up CI/CD** (Issue #25) - Automate testing
4. **Start with Phase 1 issues** - Begin implementation
5. **Weekly sync meetings** - Review progress and adjust

## Useful GitHub CLI Commands

```bash
# View issue details
gh issue view 1

# Comment on issue
gh issue comment 1 --body "Working on this now"

# Link PR to issue
gh pr create --title "Fix #1: Enable secure cookies" --body "Closes #1"

# View project board
gh project list
gh project view 1

# Check CI status
gh run list
gh run view 123
```

---

**Ready to start?** Begin with creating the labels, then the milestones, then create issues from the detailed markdown files. Good luck! 🚀
