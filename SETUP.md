# ProofGate Finance — Setup Guide

Complete walkthrough: opening a terminal, getting every API key, running the screener,
and pushing to GitHub so your team can collaborate.

---

## 1. How to open a terminal on Windows

You have three good options — use whichever feels most comfortable:

### Option A — Windows Terminal (recommended)
1. Press **Win + S**, type `Windows Terminal`, press Enter.
2. A tab opens at your user home folder (`C:\Users\tomas`).
3. Navigate to the project: paste this command and press Enter:
   ```
   cd "C:\Users\tomas\Desktop\Midnight\Projects\proofgate-finance"
   ```
4. You're in the project. Confirm with `ls` (lists the files).

### Option B — VS Code integrated terminal
1. Open VS Code (or type `code .` from Option A after navigating to the folder).
2. Press **Ctrl + `** (backtick) to open the terminal at the bottom.
3. It opens directly inside the project folder — no `cd` needed.

### Option C — PowerShell directly
1. Press **Win + S**, type `PowerShell`, right-click → "Run as administrator" if needed.
2. Same navigation: `cd "C:\Users\tomas\Desktop\Midnight\Projects\proofgate-finance"`

**For all terminal commands in this guide, assume you are inside the project folder.**

---

## 2. One-time Python setup

Run these once to install all dependencies:

```powershell
# Install everything from requirements.txt
pip install -r requirements.txt

# Verify the install worked
python -m pytest tests/ -q
```

You should see something like `36 passed in 0.3s`.

---

## 3. API keys — what you need, where to get them

### 3.1 SEC EDGAR identity (FREE — no account needed)

The SEC just asks for your name and email in a header. No sign-up, no key.

Set it like this in your `.env` file (see section 4 below):
```
SEC_IDENTITY="Tomas Garro tgarro14@gmail.com"
```

### 3.2 Anthropic API key (FREE credits on new accounts)

Used only when you run `--diff` (the AI risk factor comparison layer).

1. Go to: **https://console.anthropic.com/settings/keys**
2. Click **"Create Key"**, give it a name like `proofgate-dev`
3. Copy the key (it starts with `sk-ant-`)
4. Paste into `.env`: `ANTHROPIC_API_KEY="sk-ant-..."`

Free tier includes $5 of credits on new accounts. Each `--diff` call costs roughly $0.01–0.05.

### 3.3 FinancialModelingPrep — FMP (FREE tier)

Used by FinanceToolkit for structured financial data.
Free tier: **250 requests/day**, 5 years of history, US companies only.

1. Go to: **https://financialmodelingprep.com/developer/docs**
2. Click **"Get your Free API Key"** (top right)
3. Sign up with your email
4. Copy the key from your dashboard
5. Paste into `.env`: `FMP_API_KEY="your_key_here"`

### 3.4 Dune Analytics (FREE tier)

Dune has 100,000+ community SQL queries on blockchain data.
Free account: **2,500 execution credits/month** (cached results are free).

1. Go to: **https://dune.com/auth/register**
2. Sign up (GitHub login works great)
3. Once logged in, go to: **https://dune.com/settings/api**
4. Click **"Create new API key"**
5. Copy the key
6. Paste into `.env`: `DUNE_API_KEY="your_key_here"`

**Tip:** use `get_latest_result(query_id)` in our client to pull cached data for free.
Only use `execute_query()` when you need fresh data (costs credits).

### 3.5 Xerberus Risk API (contact for access)

Xerberus provides risk scores for Cardano, Ethereum, and Polygon tokens.
It is the best tool for Cardano native asset risk (ADA, DJED, iUSD, MIN, etc.)

1. Email: **ms@xerberus.io** with:
   - Subject: "API access request — ProofGate Finance research project"
   - Brief description: "Building a forensic finance research agent combining
     TradFi metrics with DeFi risk scoring. Planning to publish open-source."
   
   OR create an account at **https://app.xerberus.io** (some tiers available there)

2. Once you have the key, set both vars in `.env`:
   ```
   XERBERUS_API_KEY="your_key_here"
   XERBERUS_EMAIL="tgarro14@gmail.com"
   ```

Note: Xerberus requires BOTH the API key AND the email used to register.

---

## 4. Create your .env file

The `.env` file stores all your secrets locally. It is in `.gitignore` so it
will never accidentally be pushed to GitHub.

**Step 1 — Copy the template:**
```powershell
Copy-Item .env.example .env
```

**Step 2 — Open `.env` in a text editor and fill in your keys:**
```powershell
notepad .env
```

Your `.env` should look like this when filled in:
```
SEC_IDENTITY="Tomas Garro tgarro14@gmail.com"
ANTHROPIC_API_KEY="sk-ant-..."
FMP_API_KEY="abc123..."
DUNE_API_KEY="xyz789..."
XERBERUS_API_KEY="..."
XERBERUS_EMAIL="tgarro14@gmail.com"
```

**Step 3 — Load the env vars in your terminal session:**

On Windows PowerShell, run this before running any Python scripts:
```powershell
Get-Content .env | ForEach-Object {
    if ($_ -match '^([^#][^=]*)=(.*)$') {
        [System.Environment]::SetEnvironmentVariable($Matches[1].Trim(), $Matches[2].Trim().Trim('"'), 'Process')
    }
}
```

**Or** — even easier — just use `python-dotenv` which our code already does automatically.
The scripts call `load_dotenv()` at startup, so the `.env` is loaded for you.

---

## 5. Run the screener

With your `.env` filled in, run:

```powershell
# Screen a single company
python forensic_screener.py AAPL

# Screen multiple tickers
python forensic_screener.py TSLA NVDA SMCI

# Screen with AI diff layer (reads Risk Factors year-over-year)
python forensic_screener.py SMCI --diff

# Screen a DeFi protocol via DefiLlama
python forensic_screener.py --crypto aave uniswap

# Save a report
python forensic_screener.py AAPL TSLA --save-report

# Stricter M-Score threshold (-1.78 instead of -2.22)
python forensic_screener.py ENRNQ --strict-m
```

---

## 6. GitHub setup — push and add collaborators

### Step 1 — Create a GitHub account (if you don't have one)
Go to **https://github.com** and sign up.

### Step 2 — Install GitHub CLI (easiest way to push from terminal)
Download from: **https://cli.github.com**

Run the installer, then authenticate:
```powershell
gh auth login
```
Choose "GitHub.com" → "HTTPS" → "Login with a web browser". It will open your browser.

### Step 3 — Initialize git and create the repo

Run these commands one by one in your terminal (inside the project folder):

```powershell
# Initialize git
git init

# Stage everything (the .gitignore ensures .env is excluded)
git add .

# First commit
git commit -m "Initial commit: ProofGate Finance forensic screener v0.1

Beneish M-Score, Altman Z-Score, Piotroski F-Score, Sloan Accruals.
EDGAR ingestion, DefiLlama, Xerberus, and Dune clients.
Policy gate with SHA-256 audit receipts. Midnight proof experiments."

# Create the GitHub repo and push in one command
gh repo create proofgate-finance --public --source=. --push
```

This will:
- Create the repo at `github.com/YOUR_USERNAME/proofgate-finance`
- Set the remote to `origin`
- Push your code

### Step 4 — Add collaborators

```powershell
# Add Julian and team from AI Players (replace with their GitHub usernames)
gh api repos/:owner/:repo/collaborators/JULIAN_GITHUB_USERNAME -X PUT -f permission=push

# Add your data scientist
gh api repos/:owner/:repo/collaborators/DATA_SCIENTIST_USERNAME -X PUT -f permission=push

# Add the mathematician
gh api repos/:owner/:repo/collaborators/MATHEMATICIAN_USERNAME -X PUT -f permission=push
```

Or do it in the browser:
1. Go to your repo on GitHub
2. Settings → Collaborators → "Add people"
3. Search by GitHub username or email

### Step 5 — Set up branch protection (recommended before sharing)

```powershell
# Protect main branch (require PR reviews before merging)
gh api repos/:owner/:repo/branches/main/protection \
  -X PUT \
  -f required_status_checks=null \
  -f enforce_admins=false \
  -f required_pull_request_reviews='{"required_approving_review_count":1}' \
  -f restrictions=null
```

---

## 7. Day-to-day workflow for your team

```powershell
# Get latest changes
git pull origin main

# Create a feature branch for new work
git checkout -b feature/dune-holder-analysis

# After making changes, push to your branch
git add .
git commit -m "Add Dune holder concentration queries"
git push origin feature/dune-holder-analysis

# Open a pull request on GitHub
gh pr create --title "Add Dune holder analysis" --body "Adds top-holder distribution queries for Cardano tokens via Dune."
```

---

## 8. Quick reference: all API endpoints

| Source | Key in .env | Free tier | Sign-up URL |
|--------|-------------|-----------|-------------|
| SEC EDGAR | `SEC_IDENTITY` (not a key — just name + email) | Unlimited | None needed |
| Anthropic | `ANTHROPIC_API_KEY` | $5 credits | console.anthropic.com |
| FinancialModelingPrep | `FMP_API_KEY` | 250 req/day | financialmodelingprep.com |
| DefiLlama | None needed | Unlimited | None needed |
| Dune Analytics | `DUNE_API_KEY` | 2,500 credits/mo | dune.com |
| Xerberus | `XERBERUS_API_KEY` + `XERBERUS_EMAIL` | Contact for access | ms@xerberus.io |
| Nansen (optional) | `NANSEN_API_KEY` | Paid from $49/mo | nansen.ai |
| Messari (optional) | `MESSARI_API_KEY` | Free research tier | messari.io |

---

## 9. Troubleshooting

**"No module named 'src'"**
You must run Python from the project root, not from inside a subdirectory:
```powershell
# Wrong — running from inside src/
python metrics/beneish.py

# Correct — run from project root
python -c "import sys; sys.path.insert(0, '.'); exec(open('examples/full_workflow.py').read())"
```

**"edgartools: identity not set"**
Make sure your `.env` has `SEC_IDENTITY` set, or run:
```powershell
$env:SEC_IDENTITY = "Tomas Garro tgarro14@gmail.com"
```

**"Xerberus: 403 Unauthorized"**
Both `XERBERUS_API_KEY` and `XERBERUS_EMAIL` must be set. The email must match your Xerberus account.

**pytest not found**
```powershell
python -m pytest tests/ -v
```
(Use `python -m pytest` instead of bare `pytest` on Windows)
