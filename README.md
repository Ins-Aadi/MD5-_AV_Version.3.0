# Neural Defender

A signature-based file scanner with a modern desktop GUI (Tkinter).

## ⚠️ Important security note

The original uploaded `db_uploder_Domain.py` contained **live, working database
credentials** hardcoded in plain text. Those have been removed from this
codebase and replaced with environment-variable configuration. Since those
credentials were shared in this upload, **you should rotate/change them** on
your database provider as a precaution — treat them as compromised.

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Configure your database credentials:
   ```
   cp .env.example .env
   ```
   Then edit `.env` and fill in your real `ND_DB_HOST`, `ND_DB_USER`,
   `ND_DB_PASSWORD`, `ND_DB_NAME`. This file is never read by anything except
   your local app — do not commit it to git (add `.env` to `.gitignore`).

3. Your signatures table should have this shape:
   ```sql
   CREATE TABLE signatures (
       id SIGNATURE INT AUTO_INCREMENT PRIMARY KEY,
       type VARCHAR(16) NOT NULL,      -- 'hash' or 'string'
       signature TEXT NOT NULL
   );
   ```

4. Run the app:
   ```
   python main_gui.py
   ```

## Managing signatures (CLI)

```
python db_uploader.py add hash 44d88612fea8a8f36de82e1278abb02f
python db_uploader.py add string "some-malicious-marker"
python db_uploader.py list
```
This replaces the old `db_uploder_Domain.py`, which built raw SQL strings —
a SQL-injection risk. The new version uses parameterized queries only.

## What changed from the original version

| Area | Before | After |
|---|---|---|
| GUI | Fixed-size, freezes during scan | Resizable, dark theme, fully responsive during scans (threaded) |
| Scanning | File only | File **or** whole folder, with a progress bar |
| Infected files | Deleted immediately, no undo | Moved to a **quarantine** folder (`~/.neural_defender/quarantine`) after user confirmation |
| DB credentials | Hardcoded in source | Loaded from environment variables / `.env` |
| DB connections | New connection per scan | Connection pool, reused |
| `get_signatures()` failure | Returned `None` → crashed scanner | Returns `[]` → handled gracefully with a clear message |
| Error handling | Bare `except:` everywhere | Specific exceptions, logged, never silently swallowed |
| `hash()` function | Shadowed Python's builtin `hash` | Renamed `md5_hash` |
| Icon/logo paths | Relative — broke if run from another folder | Resolved relative to the script's own location |
| SQL uploader | String-built query (`cursor.execute(input)`) | Parameterized queries only |
| `st.py` (`eval()` demo) | Present, no real function | Removed |
| Logging | `print()` statements | Proper `logging` module with levels |

## Files

- `main_gui.py` – application entry point / GUI
- `engine.py` – file hashing (MD5/SHA-256)
- `scanner.py` – signature matching + quarantine logic
- `db_connect.py` – database connection pooling, reads signatures
- `db_uploader.py` – CLI tool to add/list signatures safely
- `Logo.ico`, `Logo_small.png` – app branding assets
- 
- Thankss !!!
