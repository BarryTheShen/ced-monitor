import hashlib
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
import urllib.request
import urllib.error

CED_URL = "https://apcentral.collegeboard.org/media/pdf/ap-cybersecurity-course-and-exam-description.pdf"
DATA_DIR = Path("data")
DIFF_DIR = Path("diffs")
CURRENT_PDF = DATA_DIR / "current.pdf"
HASH_FILE = DATA_DIR / "current.sha256"


def sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def download_pdf() -> Path:
    dest = DATA_DIR / "new.pdf"
    print(f"Downloading CED PDF from {CED_URL} ...")
    req = urllib.request.Request(
        CED_URL,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "application/pdf,*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://apcentral.collegeboard.org/",
        },
    )
    try:
        with urllib.request.urlopen(req) as response, open(dest, "wb") as f:
            f.write(response.read())
    except urllib.error.HTTPError as e:
        print(f"ERROR: HTTP {e.code} downloading PDF: {e.reason}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"ERROR: Failed to download PDF: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"Downloaded to {dest} ({dest.stat().st_size} bytes)")
    return dest


def generate_diff(old_pdf: Path, new_pdf: Path) -> "Path | None":
    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    diff_path = DIFF_DIR / f"{today}_diff.png"

    print(f"Generating visual diff: {old_pdf} vs {new_pdf} ...")
    try:
        result = subprocess.run(
            ["pdf-diff", str(old_pdf), str(new_pdf)],
            capture_output=True,
            timeout=300,
        )
    except FileNotFoundError:
        print("WARNING: pdf-diff binary not found. Skipping diff generation.", file=sys.stderr)
        return None
    except subprocess.TimeoutExpired:
        print("WARNING: pdf-diff timed out. Skipping diff generation.", file=sys.stderr)
        return None

    if result.returncode != 0:
        print(
            f"WARNING: pdf-diff exited with code {result.returncode}. Skipping diff.\n"
            f"stderr: {result.stderr.decode(errors='replace')}",
            file=sys.stderr,
        )
        return None

    if not result.stdout:
        print("WARNING: pdf-diff produced no output. Skipping diff.", file=sys.stderr)
        return None

    diff_path.write_bytes(result.stdout)
    print(f"Diff image saved to {diff_path} ({diff_path.stat().st_size} bytes)")
    return diff_path


def _write_github_output(**kwargs: str) -> None:
    github_output = os.environ.get("GITHUB_OUTPUT")
    if not github_output:
        return
    with open(github_output, "a") as f:
        for key, value in kwargs.items():
            f.write(f"{key}={value}\n")


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DIFF_DIR.mkdir(parents=True, exist_ok=True)

    new_pdf = download_pdf()
    new_hash = sha256(new_pdf)
    print(f"New hash: {new_hash}")

    if HASH_FILE.exists():
        old_hash = HASH_FILE.read_text().strip()
        print(f"Old hash: {old_hash}")
    else:
        old_hash = None
        print("No previous hash found (first run).")

    if new_hash == old_hash:
        print("No change detected. Exiting.")
        new_pdf.unlink()
        sys.exit(0)

    print("CHANGE DETECTED.")

    diff_path = None
    if CURRENT_PDF.exists() and old_hash is not None:
        diff_path = generate_diff(CURRENT_PDF, new_pdf)
    else:
        print("No previous PDF — skipping diff generation.")

    # Replace current.pdf with the new download
    new_pdf.replace(CURRENT_PDF)
    print(f"Updated {CURRENT_PDF}")

    # Persist new hash
    HASH_FILE.write_text(new_hash)
    print(f"Updated {HASH_FILE}")

    # Signal to GitHub Actions
    output: dict[str, str] = {"changed": "true"}
    if diff_path is not None:
        output["diff_image"] = str(diff_path)
    _write_github_output(**output)

    print("Done. Exiting with success.")


if __name__ == "__main__":
    main()
