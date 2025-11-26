"""Initialize repository from agent-engine-cicd-base template.

This script automates the package name replacement process when creating
a new repository from the template. Run once after creating from template:

    uv run init-template

The script performs:
- Directory renaming (src/agent_engine_cicd_base → src/{package_name})
- File content updates (package imports, configuration, documentation)
- CHANGELOG.md replacement with fresh template
- UV lockfile regeneration

Reusing in other template projects:
    To adapt this script for another template repository, update the constants:
    - ORIGINAL_PACKAGE_NAME: The original Python package name (snake_case)
    - ORIGINAL_REPO_NAME: The original repository name (kebab-case)
"""

import re
import subprocess
import sys
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import NoReturn

from pydantic import ValidationError

from .config import TemplateConfig

# Original template names - update these when reusing in other template projects
ORIGINAL_PACKAGE_NAME = "agent_engine_cicd_base"
ORIGINAL_REPO_NAME = "agent-engine-cicd-base"

# Output file names for logging results
DRY_RUN_OUTPUT_FILE = "init_template_dry_run.md"
ACTUAL_RUN_OUTPUT_FILE = "init_template_results.md"


class DualOutput:
    """Write to both stdout and a file simultaneously.

    This class wraps stdout to capture all print statements and write them
    to both the terminal and a markdown file.
    """

    def __init__(self, file_path: Path) -> None:
        """Initialize dual output handler.

        Args:
            file_path: Path to markdown file for logging output.
        """
        self.terminal = sys.stdout
        self.log_file = file_path.open("w")
        self._write_header()

    def _write_header(self) -> None:
        """Write markdown header to log file."""
        timestamp = datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
        self.log_file.write("# Template Initialization Log\n\n")
        self.log_file.write(f"**Timestamp:** {timestamp}\n\n")
        self.log_file.write("---\n\n")
        self.log_file.flush()

    def write(self, message: str) -> None:
        """Write message to both terminal and file.

        Args:
            message: Text to write.
        """
        self.terminal.write(message)
        self.log_file.write(message)

    def flush(self) -> None:
        """Flush both output streams."""
        self.terminal.flush()
        self.log_file.flush()

    def close(self) -> None:
        """Close the log file."""
        self.log_file.close()


@contextmanager
def dual_output_context(dry_run: bool = False) -> Generator[None]:
    """Context manager for dual output (terminal + file).

    Args:
        dry_run: If True, use dry-run output file, otherwise use actual output file.

    Yields:
        None. Redirects sys.stdout to DualOutput during context.
    """
    output_file = DRY_RUN_OUTPUT_FILE if dry_run else ACTUAL_RUN_OUTPUT_FILE
    output_path = Path(output_file)

    dual_out = DualOutput(output_path)
    original_stdout = sys.stdout
    sys.stdout = dual_out

    try:
        yield
    finally:
        sys.stdout = original_stdout
        dual_out.close()
        print(f"\n📄 Output saved to: {output_file}")  # This prints to terminal only


def parse_github_remote_url(url: str) -> dict[str, str] | None:
    """Parse GitHub owner and repo from remote URL.

    Supports both SSH and HTTPS formats:
    - SSH: git@github.com:owner/repo.git
    - HTTPS: https://github.com/owner/repo.git

    Args:
        url: Git remote URL to parse.

    Returns:
        Dictionary with 'owner' and 'repo' keys, or None if not a GitHub URL.
    """
    # SSH format: git@github.com:owner/repo.git
    ssh_match = re.match(r"^git@github\.com:([^/]+)/(.+?)(?:\.git)?$", url)
    if ssh_match:
        return {"owner": ssh_match.group(1), "repo": ssh_match.group(2)}

    # HTTPS format: https://github.com/owner/repo.git
    https_match = re.match(r"^https://github\.com/([^/]+)/(.+?)(?:\.git)?$", url)
    if https_match:
        return {"owner": https_match.group(1), "repo": https_match.group(2)}

    return None


def get_repo_name_from_git() -> str | None:
    """Get repository name from git remote URL.

    Returns:
        Repository name from origin remote, or None if unavailable.
    """
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],  # noqa: S603, S607
            capture_output=True,
            text=True,
            check=True,
        )
        url = result.stdout.strip()
        parsed = parse_github_remote_url(url)
        return parsed["repo"] if parsed else None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def get_validated_config(dry_run: bool = False) -> TemplateConfig:
    """Auto-detect and validate repository configuration.

    This function enforces Python package naming conventions by validating
    the repository name is kebab-case. If the repository name doesn't conform,
    the script fails with instructions to create a new repository with proper
    naming.

    Args:
        dry_run: If True, skip detection and use example values.

    Returns:
        Validated TemplateConfig instance with package_name derived from repo_name.

    Raises:
        SystemExit: If repository name is not detected or invalid.
    """
    if dry_run:
        print("🔍 DRY RUN MODE - Using example values\n")
        return TemplateConfig(repo_name="my-agent")

    print("🚀 Initializing repository from template\n")
    print("This script will:")
    print("  1. Validate repository name (must be kebab-case)")
    print(f"  2. Rename src/{ORIGINAL_PACKAGE_NAME}/ to your package name")
    print("  3. Update configuration files")
    print("  4. Update documentation")
    print("  5. Reset CHANGELOG.md")
    print("  6. Regenerate UV lockfile\n")

    # Auto-detect repository name from git
    detected_repo = get_repo_name_from_git()

    if not detected_repo:
        print("❌ Failed to detect repository name from git remote.\n")
        print("This script requires a git repository with a configured remote.")
        print("\nPlease ensure:")
        print("  1. You created this repository from the template on GitHub")
        print("  2. You cloned it locally (git clone)")
        print("  3. The remote is configured (git remote -v)\n")
        sys.exit(1)

    print(f"✨ Detected repository name: {detected_repo}\n")

    # Validate repository name conforms to kebab-case
    try:
        config = TemplateConfig(repo_name=detected_repo)
        print("✅ Repository name is valid kebab-case")
        print(f"✨ Package name (auto-derived): {config.package_name}\n")
        return config
    except ValidationError:
        print(f"❌ Invalid repository name: '{detected_repo}'\n")
        print("Repository names must follow kebab-case naming:")
        print("  • Use lowercase letters, numbers, and hyphens only")
        print("  • Cannot start or end with a hyphen")
        print("  • Examples: my-agent, agent-v2, cool-app\n")
        print("To fix this:")
        print("  1. Delete this repository on GitHub")
        print("  2. Create a new repository from the template with a kebab-case name")
        print("  3. Clone the new repository")
        print("  4. Run this init script again\n")
        sys.exit(1)


def replace_in_file(
    file_path: Path, replacements: dict[str, str], dry_run: bool = False
) -> None:
    """Perform text replacements in a file.

    Args:
        file_path: Path to file to modify.
        replacements: Dictionary mapping old strings to new strings.
        dry_run: If True, only print what would be changed.
    """
    if not file_path.exists():
        print(f"  ⚠️  Skipping {file_path} (not found)")
        return

    content = file_path.read_text()
    modified = content

    for old, new in replacements.items():
        modified = modified.replace(old, new)

    if content != modified:
        if dry_run:
            print(f"  📝 Would update {file_path}")
        else:
            file_path.write_text(modified)
            print(f"  ✅ Updated {file_path}")
    else:
        if dry_run:
            print(f"  ⏭️  Would skip {file_path} (no changes needed)")


def replace_changelog(dry_run: bool = False) -> None:
    """Replace CHANGELOG.md with fresh template.

    Args:
        dry_run: If True, only print what would be changed.
    """
    changelog_path = Path("CHANGELOG.md")

    fresh_changelog = """# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project setup from template
"""

    if dry_run:
        print("  📝 Would replace CHANGELOG.md with fresh template")
    else:
        changelog_path.write_text(fresh_changelog)
        print("  ✅ Replaced CHANGELOG.md")


def run_uv_sync(dry_run: bool = False) -> None:
    """Regenerate UV lockfile.

    Args:
        dry_run: If True, only print what would be done.
    """
    if dry_run:
        print("  📝 Would run: uv sync")
        return

    print("  🔄 Running uv sync...")
    try:
        subprocess.run(
            ["uv", "sync"],  # noqa: S603, S607
            check=True,
            capture_output=True,
        )
        print("  ✅ UV lockfile regenerated")
    except subprocess.CalledProcessError as e:
        print(f"  ❌ Failed to run uv sync: {e}")
        print(f"     stderr: {e.stderr.decode()}")
        sys.exit(1)


def print_summary(config: TemplateConfig, dry_run: bool = False) -> None:
    """Print summary of changes.

    Args:
        config: Validated template configuration.
        dry_run: If True, prefix all messages with "Would".
    """
    verb = "Would make" if dry_run else "Made"
    print(f"\n✅ {verb} the following changes:")
    print(f"  • Package name: {ORIGINAL_PACKAGE_NAME} → {config.package_name}")
    print(f"  • Repo name: {ORIGINAL_REPO_NAME} → {config.repo_name}")
    print(f"  • Directory: src/{ORIGINAL_PACKAGE_NAME}/ → src/{config.package_name}/")
    print("  • Updated configuration and test files")
    print("  • Replaced CHANGELOG.md with fresh template")
    print("  • Regenerated UV lockfile")

    if not dry_run:
        print("\n🎉 Template initialization complete!")
        print("\nNext steps:")
        print("  1. Review changes: git status")
        print("  2. Create .env file: cp .env.example .env")
        print("  3. Configure .env with your GCP project details")
        print("  4. Test locally: uv run local-agent")
        print(
            "  5. Commit: git add -A && git commit -m 'chore: initialize from template'"
        )
    else:
        print("\n💡 Run without --dry-run to apply these changes")


def main() -> NoReturn:
    """Main initialization function."""
    # Check for dry-run flag
    dry_run = "--dry-run" in sys.argv

    # Run with dual output (terminal + markdown file)
    with dual_output_context(dry_run):
        # Get and validate configuration
        config = get_validated_config(dry_run)

        # Define replacements
        replacements = {
            ORIGINAL_PACKAGE_NAME: config.package_name,
            ORIGINAL_REPO_NAME: config.repo_name,
        }

        # Files to update (paths relative to repo root)
        files_to_update = [
            "pyproject.toml",
            "tests/test_config.py",
            "tests/conftest.py",
            "README.md",
        ]

        # Rename directory
        old_dir = Path(f"src/{ORIGINAL_PACKAGE_NAME}")
        new_dir = Path(f"src/{config.package_name}")

        if old_dir.exists():
            print("\n📁 Renaming directory:")
            if dry_run:
                print(f"  📝 Would rename {old_dir} → {new_dir}")
            else:
                old_dir.rename(new_dir)
                print(f"  ✅ Renamed {old_dir} → {new_dir}")
        else:
            print(f"\n⚠️  Directory {old_dir} not found - already renamed?")

        # Update files
        print("\n📝 Updating files:")
        for file_path_str in files_to_update:
            file_path = Path(file_path_str)
            replace_in_file(file_path, replacements, dry_run)

        # Replace CHANGELOG
        print("\n📄 Replacing CHANGELOG:")
        replace_changelog(dry_run)

        # Regenerate lockfile
        print("\n🔒 Regenerating lockfile:")
        run_uv_sync(dry_run)

        # Print summary
        print_summary(config, dry_run)

    sys.exit(0)


if __name__ == "__main__":
    main()
