# Code Quality Automation with GitHub Actions

The code quality automation uses a **conditional workflow strategy** that only runs expensive quality checks (formatting, linting, type checking) when relevant files are changed.

## Workflow Architecture

The automation consists of two GitHub Actions workflows:

### 1. Required Checks (`required-checks.yml`)
**Primary workflow that orchestrates the entire process:**

- **Triggers**: Runs on all pull requests
- **Path Detection**: Uses `dorny/paths-filter` to detect changes to relevant files
- **Conditional Execution**: Only calls the quality workflow if code files changed
- **Status Aggregation**: Always runs a final status job for branch protection compatibility

### 2. Code Quality (`code-quality.yml`) 
**Reusable workflow that performs the actual quality checks:**

- **Triggers**: `workflow_call` (called by other workflows) and `workflow_dispatch` (manual)
- **Multi-version Testing**: Runs on Python 3.12 and 3.13
- **Quality Tools**: Ruff formatting, Ruff linting, and MyPy type checking
- **Fail-fast Disabled**: All checks run even if one fails for complete feedback

## File Change Detection

The automation monitors these file patterns:

```yaml
filters: |
  code:
    - '**.py'                                   # All Python files (recursive)
    - 'pyproject.toml'                          # Package configuration
    - 'uv.lock'                                 # Dependency lock file
    - '.github/workflows/code-quality.yml'      # Quality workflow changes
    - '.github/workflows/required-checks.yml'   # Main workflow changes
```

**When files match these patterns**: Quality checks run automatically
**When only other files change** (e.g., `README.md`, `docs/`): Quality checks are skipped

## Branch Protection Setup

To enforce code quality standards, configure branch protection to require the `required-status` job.

### GitHub UI Method

1. **Navigate to Settings**:
   - Go to your repository on GitHub
   - Click **Settings** → **Branches**

2. **Edit Branch Protection Rule**:
   - Find the existing rule for `main` branch and click **Edit**
   - Enable **"Require status checks to pass before merging"**
   - Check **"Require branches to be up to date before merging"** (recommended)

3. **Select Required Status Checks**:
   - In the **"Status checks that are required"** section, search for: `Required Checks / required-status`
   - Select the status check from the search results
   - Click **Save changes**

**Note**: The status check will only appear in the search after the workflow has run at least once on a pull request.

### Verification

Once configured, you can verify the branch protection is working by checking that PRs are blocked when the `Required Checks / required-status` check fails.

## How It Works

### Scenario 1: Python Code Changes
```
PR Created → Path Filter Detects Python Files → Quality Checks Run → Status Reported
```

1. Developer creates PR with Python file changes
2. `required-checks.yml` runs path detection
3. Code changes detected → `code-quality.yml` workflow executes
4. Quality tools run: Ruff format, Ruff lint, MyPy type check
5. `required-status` job reports success/failure
6. Branch protection enforces the result

### Scenario 2: Documentation-Only Changes
```
PR Created → Path Filter Detects No Code → Quality Checks Skipped → Success Reported
```

1. Developer creates PR with only documentation changes
2. `required-checks.yml` runs path detection  
3. No code changes detected → Quality workflow skipped
4. `required-status` job reports success (no quality issues possible)
5. PR can merge without running expensive checks


## Monitoring and Troubleshooting

### View Workflow Status
```bash
# List recent workflow runs
gh run list --workflow="required-checks.yml"

# View specific run details
gh run view <run-id>

# Watch logs in real-time
gh run watch <run-id>
```

### Common Issues

**Issue**: Workflow permissions errors
- **Check**: Repository workflow permissions in Settings → Actions → General
- **Solution**: Ensure "Read and write permissions" are enabled for `GITHUB_TOKEN`

### Debugging Tips

1. **Check Path Filter Output**: Look for the `check-changes` job output to see which files triggered the filter

2. **Verify Workflow Triggers**: Ensure workflows are triggering on the correct events (`pull_request` for required-checks)

3. **Review Job Dependencies**: The `required-status` job depends on both `check-changes` and `code-quality` jobs

4. **Test Locally**: Run quality commands locally to verify they work:
   ```bash
   uv run ruff format --check
   uv run ruff check
   uv run mypy
   ```

## Manual Quality Checks

Developers can run quality checks locally before creating PRs:

```bash
# Run all quality checks at once
uv run ruff format && uv run ruff check && uv run mypy

# Run individual tools
uv run ruff format      # Format code with Ruff
uv run ruff check       # Lint code with Ruff  
uv run mypy             # Type-check with MyPy
```

## Benefits

- **Resource Efficiency**: Only runs quality checks when needed
- **Fast Feedback**: Immediate quality feedback on code changes
- **Selective Enforcement**: Documentation changes don't require code quality
- **Developer Friendly**: Clear status reporting and helpful error messages
- **Scalable**: Works for repositories of any size without performance issues

## Best Practices

1. **Run Locally First**: Test quality checks locally before pushing
2. **Small PRs**: Keep changes focused to get faster feedback
3. **Fix Issues Promptly**: Address quality check failures immediately
4. **Update Dependencies**: Keep `uv.lock` updated to avoid version conflicts
5. **Monitor Performance**: Watch for any degradation in workflow execution time

## Resources

**[← Back to Documentation](../README.md#documentation)**
