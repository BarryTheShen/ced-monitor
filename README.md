# CED Monitor

Automatically monitors the [College Board AP Cybersecurity Course and Exam Description (CED)](https://apcentral.collegeboard.org/media/pdf/ap-cybersecurity-course-and-exam-description.pdf) PDF for changes.

Runs daily via GitHub Actions. When a change is detected, it generates a **visual diff image** (red outlines around changed text) and sends an email notification.

---

## How it works

1. Downloads the CED PDF from College Board.
2. Computes a SHA-256 hash of the downloaded file.
3. Compares the hash against the previously stored hash.
4. **No change:** exits silently — no commit, no email.
5. **Change detected:**
   - Runs [`pdf-diff`](https://github.com/JoshData/pdf-diff) to generate a PNG with red outlines around changed text.
   - Saves the diff image to `diffs/YYYY-MM-DD_diff.png`.
   - Updates `data/current.pdf` and `data/current.sha256`.
   - Commits and pushes the updated files.
   - Sends an email notification with a link to the diff.

---

## Repository structure

```
ced-monitor/
├── .github/workflows/check-ced.yml   # GitHub Actions workflow (runs daily)
├── check.py                          # Main detection script
├── requirements.txt                  # Python dependencies
├── data/
│   ├── current.pdf                   # Latest known CED PDF
│   └── current.sha256                # SHA-256 hash of current PDF
└── diffs/
    └── <YYYY-MM-DD>_diff.png         # Visual diffs (accumulate over time)
```

---

## Setup

### 1. Initial baseline

Run once locally to capture the current PDF before the first scheduled run:

```bash
pip install -r requirements.txt
sudo apt-get install poppler-utils   # or brew install poppler on macOS
python check.py
```

Commit the resulting `data/current.pdf` and `data/current.sha256`.

### 2. GitHub Secrets (for email notifications)

Go to **Settings → Secrets and variables → Actions** and add:

| Secret | Value |
|---|---|
| `EMAIL_USERNAME` | Your Gmail address (e.g. `you@gmail.com`) |
| `EMAIL_PASSWORD` | A [Gmail App Password](https://myaccount.google.com/apppasswords) (16 characters) |

> Email is optional. If secrets are not set, the workflow will still detect changes and commit diffs — only the email step will fail.

### 3. Test the workflow

Go to **Actions → Check CED for Changes → Run workflow** to trigger manually.

---

## Schedule

Runs daily at **17:00 UTC** (1:00 AM Beijing time / CST).
