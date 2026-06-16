import re
import subprocess
import json
from pathlib import Path

def get_github_repo_path(root_dir: Path) -> str | None:
    git_config = root_dir / '.git' / 'config'
    if not git_config.exists():
        return None
    try:
        content = git_config.read_text(encoding='utf-8')
        match = re.search(r'url\s*=\s*(?:git@github\.com:|https://github\.com/)([^/\s]+/[^/\s\.]+)(?:\.git)?', content)
        if match:
            return match.group(1)
    except Exception:
        pass
    return None

def publish_git_release(root_dir: Path, version: str, progress_cb=None) -> bool:
    def log(msg, level='info'):
        if progress_cb:
            progress_cb(msg, level)
        else:
            print(f"[{level.upper()}] {msg}")

    repo = get_github_repo_path(root_dir)
    if not repo:
        log('Git repository or GitHub remote origin not found in .git/config.', 'error')
        return False

    tag = f'v{version}'
    log(f'Preparing release for repository: {repo} (Tag: {tag})', 'info')

    # 1. Update update.json in the root folder
    update_file = root_dir / 'update.json'
    update_data = {
        'version': version,
        'url': f'https://github.com/{repo}/releases/download/{tag}/EveryThingDownloader-Portable-{version}.exe',
        'changelog': f'Phiên bản mới nhất {tag} được phát hành qua Build Tool.'
    }
    
    try:
        with open(update_file, 'w', encoding='utf-8') as f:
            json.dump(update_data, f, indent=4)
        log('Generated update.json locally.', 'ok')
    except Exception as e:
        log(f'Failed to write update.json: {e}', 'error')
        return False

    # 2. Run git commands
    try:
        # Check if git is installed and command runs
        subprocess.run(['git', '--version'], capture_output=True, check=True)
        
        # Stage all changes in the repository to ensure all code updates are included in the build
        log('Staging all local changes (git add -A)...', 'info')
        subprocess.run(['git', 'add', '-A'], cwd=str(root_dir), check=True)
        
        # Check if there are changes staged
        diff_check = subprocess.run(['git', 'diff', '--cached', '--quiet'], cwd=str(root_dir))
        if diff_check.returncode != 0:
            subprocess.run(['git', 'commit', '-m', f'release: publish version {tag}'], cwd=str(root_dir), check=True)
            log(f'Committed all changes to local repository under tag {tag}.', 'ok')
        else:
            log('No local changes to commit.', 'info')

        # Create tag locally (force override if exists)
        subprocess.run(['git', 'tag', '-f', tag, '-m', f'Release {tag}'], cwd=str(root_dir), check=True)
        log(f'Created local tag: {tag}', 'ok')

        # Find current branch
        branch_res = subprocess.run(['git', 'branch', '--show-current'], cwd=str(root_dir), capture_output=True, text=True, check=True)
        current_branch = branch_res.stdout.strip() or 'main'
        
        log(f'Pushing current branch ({current_branch}) to remote origin...', 'info')
        subprocess.run(['git', 'push', 'origin', current_branch], cwd=str(root_dir), check=True)
        
        log(f'Pushing tag ({tag}) to remote origin...', 'info')
        subprocess.run(['git', 'push', 'origin', '-f', tag], cwd=str(root_dir), check=True)
        
        log(f'Successfully published git release {tag}! GitHub Actions will now build and package this release.', 'ok')
        return True
    except subprocess.CalledProcessError as e:
        # Try to capture output
        err_msg = getattr(e, 'stderr', None) or str(e)
        log(f'Git operation failed: {err_msg}', 'error')
        return False
    except Exception as e:
        log(f'An unexpected error occurred during git release: {e}', 'error')
        return False
