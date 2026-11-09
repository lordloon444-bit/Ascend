# ASCEND · GitHub Pages + Private Cloud Sync

This is an **upgrade of the existing ASCEND v10 dashboard**, not a replacement. The Daily Tracker remains the homepage; the existing Vision Board, Journal, Fitness Tracker, Goal Tracker, Affirmations, animations, mobile navigation, and glass styling are preserved.

The app is fully static: `index.html` contains the existing dashboard, CSS, artwork, 110 affirmations, and its JavaScript. No server or build pipeline is required. Cloud synchronization uses GitHub's REST API directly **from the browser**. The only new UI is the compact Cloud Backup & Sync panel, opened from the top bar.

## 1. Create two separate repositories

Create these repositories under your GitHub account:

| Repository | Visibility | Purpose |
|---|---|---|
| `ASCEND` | **Public** for straightforward GitHub Pages hosting | Website source only |
| `ASCEND-Data` | **Private** | Personal data, current backup, and recovery snapshots |

Initialize `ASCEND-Data` with a README, so its default branch exists. **The branch must be named `main`.** Do not put any personal backup or token in the public `ASCEND` repo. You can use a private `ASCEND` source repository only if your GitHub account's Pages entitlements allow it; public source is the simpler setup.

## 2. Deploy the existing website

Upload the **contents** of this package (not the enclosing folder) into `ASCEND`:

```text
ASCEND/
├── index.html
├── .nojekyll
├── .gitignore
├── README.md
└── .github/
    └── workflows/
        └── deploy.yml
```

Using git from the unpacked package directory:

```bash
git init -b main
git remote add origin https://github.com/YOUR_USERNAME/ASCEND.git
git add index.html .nojekyll .gitignore README.md .github/workflows/deploy.yml
git commit -m "Deploy ASCEND with private cloud sync"
git push -u origin main
```

If `ASCEND` already exists with an initial commit, clone it first and copy these files into the clone instead of running `git init`. If git asks for a username or password during a push, use GitHub's normal authenticated git workflow; **do not use the restricted `ASCEND-Data` token for deploying the website**.

Then in **ASCEND → Settings → Pages**, choose **Build and deployment → Source: GitHub Actions**. The included workflow publishes on pushes to `main`, using GitHub's official Pages actions. Check **Actions** for a successful deployment.

Your project URL will be:

`https://YOUR_USERNAME.github.io/ASCEND/`

There are no root-relative asset paths or client-side router redirects: everything loads from this project URL. All artwork stays bundled in `index.html`.

## 3. Create the restricted GitHub data token

In GitHub, open **Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token**.

Use these settings:

1. **Resource owner:** the account that owns `ASCEND-Data`.
2. **Repository access:** Only select repositories → `ASCEND-Data` (and no other repository).
3. **Repository permissions:** Contents → **Read and write**. GitHub grants required Metadata read access automatically.
4. Set a reasonable **expiration date**, then generate and copy the token privately.

Do not paste the token into this repo, README, code, issue, commit, cloud backup, or screenshot. The website does not embed a token.

## 4. Connect ASCEND from each device

1. Open the published ASCEND website and click the **Cloud status** control in the top bar.
2. Enter your GitHub username (or organization name) and paste your fine-grained token.
3. Leave **Keep the token on this device** unchecked unless you explicitly accept the security warning.
4. Click **Connect GitHub**.
5. If the data repository has no `data/latest.json`, ASCEND will prepare its first upload. If cloud data already exists, ASCEND compares it with local data and **asks what to do** if they differ.

With memory-only credentials, reconnect after every page reload or browser restart. The optional persistent mode saves the token **unencrypted** in the browser's local storage and carries risk on shared devices, browser extensions, and compromised pages. Disconnect removes any stored token.

For a new device: **Connect → Use Cloud** when the comparison panel appears. Other choices are **Keep Local & Upload** (explicitly confirms replacing the cloud backup) or **Resolve Selected** (choose local/cloud separately for Daily Tracker, Goals, Fitness Tracker, and Journal + attachments).

**Important migration note:** Browser storage is origin-specific. Progress previously saved by opening `ASCEND_v10.html` as a local file will not automatically appear under `https://YOUR_USERNAME.github.io/ASCEND/`. Before switching, export a JSON backup from v10 and **import that file into the hosted ASCEND**, or first sync it using the new version on the previous origin. Do not erase or clear your old browser data until you verify the new copy.

## 5. Cloud Sync settings and behavior

The top-bar status indicator reports exactly one of:

- **Saved Locally**: the local write succeeded, but a newer GitHub write has not yet been confirmed.
- **Syncing**: checking remote state and/or uploading.
- **Synced**: GitHub's API confirmed the write, or the local and remote payloads were verified identical.
- **Offline**: sync is waiting for a connection, without discarding local work.
- **Conflict**: competing versions or an HTTP 409/422 require explicit resolution.
- **Error**: authentication, validation, storage, or server trouble prevented confirmed sync.

Settings include auto-sync on/off, debounce (default **10 seconds**, 2–120), recovery snapshot frequency (default **24 hours**, 1–168), and maximum retained snapshots (default **10**, 1–50). Changes save locally immediately; cloud writes are serialized, and the client checks the latest blob SHA before replacing data. It retries temporary network/server/rate-limit failures with exponential backoff and never claims a successful write without a positive GitHub API response.

- **Sync Now** checks remote state and uploads only if needed.
- **Restore from Cloud** opens the version choice dialog instead of silently overwriting this device.
- **Backup History** lists recovery snapshots; individual snapshots can be downloaded or restored after confirmation through the version choice dialog.
- **Export JSON / Import JSON** reuse the existing ASCEND backup controls and format.

Auto-sync runs **only while the dashboard page is open**. This is not a native push-notification service. Changes made offline stay in browser storage and sync once the page is connected and the internet works.

## 6. Private repository data layout

After the first successful upload, `ASCEND-Data` contains:

```text
ASCEND-Data/       (PRIVATE)
├── README.md
├── data/
│   └── latest.json
└── snapshots/
    ├── 2026-…-DEVICE.json
    └── …
```

`latest.json` uses a versioned envelope, initially `schemaVersion: 1`, containing the **original `ASCEND-v3` data shape**: `journal`, `goals`, `workouts`, `dailyTasks`, and `files` (journal attachments as Base64 data URLs). This preserves the existing `ascend-v3-*` local-storage keys, existing per-exercise workout records, checkmark states, recurrence settings, and text entries. Journal attachments are still stored in IndexedDB on the device, but are serialized **with their actual bytes** in exported and cloud backups. A missing attachment causes cloud upload to fail rather than silently omitting it.

Vision Board artwork and the 110 affirmation phrases are **already embedded in the website source**, not stored as browser object URLs; they work offline and on every device without extra uploads. The current dashboard does not expose editable vision-board image uploads or persistent affirmation preferences, so there is no additional user-defined state in those modules to migrate. Future storage fields should be added to the schema and migration tests before release.

Unsupported future schema versions are rejected rather than guessed. Older plain `ASCEND-v3` JSON exports can still be imported. Cloud restore attempts to retain/roll back previous local values if storage fails.

Each snapshot is a recovery point, **not a new independent set of tokens or a copy of the website**. By default ASCEND creates a snapshot no more frequently than every 24 hours, then trims older snapshots. Commit volume scales with actual changes, plus periodic snapshots and pruning, not with every keystroke.

Because GitHub Contents API reads/writes operate on whole files, ASCEND limits cloud JSON to **35 MB**. For larger journals or many attached PDFs, use Export JSON and consider a purpose-built storage backend instead. `ASCEND-Data` is private, but GitHub itself stores those contents as ordinary private-repo files, **not end-to-end-encrypted ciphertext**.

## 7. Security and operational limits

- Keep **`ASCEND` and `ASCEND-Data` separate**. `ASCEND` is only source code; `ASCEND-Data` must stay private.
- The token is never included in the HTML bundle, URL, Cloud API payloads, JSON export, or logs.
- A public static web app cannot protect an explicitly persisted browser token from malicious same-origin scripts or sufficiently privileged extensions. Memory-only is the default and safer option.
- The private data repo must be on `main`. The website token does **not** need access to the public source repo.
- The site needs internet access to `api.github.com` for sync. Browser/network privacy settings can interfere with outbound authenticated requests.
- GitHub `409` conflicts **stop synchronization** and require review; no automatic last-writer-wins overwrite.
- Keep a periodic offline JSON export, especially before changing devices or browser profiles.

## 8. Tests performed and not performed

Tested locally with Chromium's DOM execution and a mocked GitHub REST API: original page initialization, six-page navigation, local writes, initial upload, GitHub response validation, snapshots, no-change sync without extra commits, cross-device restore and conflict choices, SHA mismatches/HTTP 409, offline state, temporary 503 + retry, backup history, and binary journal attachment serialization and restoration. All test tokens were dummy strings.

**Not verified against live GitHub:** actual authentication, API CORS/network behavior, live commits, a real Actions deployment, and the published URL. Browser navigation was restricted in the test environment, so the GitHub Pages subpath was reviewed statically: the site uses one self-contained `index.html`, has no absolute asset paths, and doesn't require server routing. Complete a real two-device smoke test after deployment before depending on it as your only backup.

GitHub reference documentation:

- [Repository Contents API](https://docs.github.com/en/rest/repos/contents)
- [Deploying a static website with Actions](https://docs.github.com/en/get-started/start-your-journey/deploying-your-website-automatically)
- [Publishing from a GitHub Actions workflow](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)
