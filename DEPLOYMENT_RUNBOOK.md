# ConnectLink - Deployment & Operations Runbook

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Installation on Windows](#installation-windows)
3. [Installation on macOS/Linux](#installation-macos-linux)
4. [Installation on Production Server](#installation-production)
5. [Multi-Branch POS (Shurugwi + Chegutu)](#multi-branch-pos-shurugwi--chegutu)
6. [Configuration & Setup](#configuration)
7. [Database Management](#database-management)
8. [Backup & Recovery](#backup-recovery)
9. [Monitoring & Maintenance](#monitoring)
10. [Troubleshooting](#troubleshooting)
11. [Upgrade Procedures](#upgrade)

---

## PRE-DEPLOYMENT CHECKLIST

### System Requirements
```
✓ Operating System: Windows 10+, macOS 10.14+, or Linux (Ubuntu 20.04+)
✓ Python: 3.8 or higher
✓ PostgreSQL: 12 or higher
✓ Server RAM: 2GB minimum (4GB recommended)
✓ Storage: 10GB minimum (20GB recommended)
✓ Internet: Required for API integrations
✓ Domain/IP: For public access
```

### Pre-Deployment Tasks
- [ ] Verify system meets requirements
- [ ] Check internet connectivity
- [ ] Install PostgreSQL
- [ ] Create PostgreSQL user account
- [ ] Create database `connectlinkdata`
- [ ] Obtain API keys:
  - Google Gemini API key
  - WhatsApp Business API token
  - (Optional) SendGrid email service key
- [ ] Reserve production domain/IP address
- [ ] Plan backup strategy
- [ ] Assign user roles and permissions
- [ ] Document configuration details

---

## INSTALLATION ON WINDOWS

### Step 1: Install Python 3.8+

**Download**:
1. Visit: https://www.python.org/downloads/
2. Download Python 3.11+ (latest stable)
3. Run installer
4. **IMPORTANT**: Check "Add Python to PATH"
5. Click "Install Now"

**Verify**:
```cmd
python --version
pip --version
```

### Step 2: Install Git

**Download**:
1. Visit: https://git-scm.com/download/win
2. Download Git for Windows
3. Run installer
4. Use default options

**Verify**:
```cmd
git --version
```

### Step 3: Install PostgreSQL

**Download**:
1. Visit: https://www.postgresql.org/download/windows/
2. Download PostgreSQL 12 or higher
3. Run installer
4. Set password for `postgres` user (save this!)
5. Use port 5432 (default)
6. Complete installation

**Verify**:
```cmd
psql --version
```

### Step 4: Create Database & User

**Open PostgreSQL Command Line**:
```cmd
psql -U postgres
```

**Create User**:
```sql
CREATE USER connectlink_user WITH PASSWORD 'your_secure_password';
ALTER ROLE connectlink_user WITH CREATEDB;
```

**Create Database**:
```sql
CREATE DATABASE connectlinkdata OWNER connectlink_user;
GRANT ALL PRIVILEGES ON DATABASE connectlinkdata TO connectlink_user;
```

**Verify**:
```sql
\l  -- List databases
\du -- List users
```

**Exit**:
```sql
\q
```

### Step 5: Clone ConnectLink Repository

**Choose Installation Directory**:
```cmd
cd Documents
```

**Clone Repository**:
```cmd
git clone https://github.com/yourusername/connectlink.git
cd connectlink
```

### Step 6: Create Virtual Environment

```cmd
python -m venv venv
venv\Scripts\activate
```

**Verify** (you should see `(venv)` in prompt):
```cmd
where python
```

### Step 7: Install Python Dependencies

```cmd
pip install --upgrade pip
pip install -r requirements.txt
```

**Wait for completion** (2-5 minutes)

### Step 8: Create Environment Configuration

**Create `.env` file** (in connectlink folder):
```
# Database
DATABASE_URL=postgresql://connectlink_user:your_secure_password@localhost:5432/connectlinkdata

# Flask
FLASK_APP=ConnectLink.py
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=your_super_secret_key_here_change_in_production

# API Keys
GEMINI_API_KEY=your_gemini_api_key_here
WHATSAPP_API_TOKEN=your_whatsapp_api_token_here
WHATSAPP_PHONE_ID=your_whatsapp_phone_id_here

# Email (Optional)
SENDGRID_API_KEY=your_sendgrid_api_key_here

# Application
APP_URL=http://localhost:5000
SESSION_TIMEOUT=3600
```

### Step 9: Initialize Database

**First Time Run**:
```cmd
python ConnectLink.py
```

**Wait for**:
- Database tables created
- System initialized
- Server starts on port 5000

**Expected Output**:
```
 * Running on http://127.0.0.1:5000
 * WARNING: This is a development server. Do not use it in production.
```

### Step 10: Access the Application

Open browser and go to:
```
http://localhost:5000
```

**Default Login** (create after first setup):
- Username: admin
- Password: (set during setup)

---

## INSTALLATION ON MACOS/LINUX

### Step 1: Install System Dependencies

**macOS**:
```bash
# Install Homebrew first if not installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install python@3.11
brew install postgresql
```

**Ubuntu/Debian**:
```bash
sudo apt update
sudo apt install python3.11 python3.11-venv postgresql postgresql-contrib git
```

### Step 2: Verify Installations

```bash
python3.11 --version
psql --version
git --version
```

### Step 3: Start PostgreSQL Service

**macOS**:
```bash
brew services start postgresql
```

**Ubuntu/Debian**:
```bash
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### Step 4: Create Database User

```bash
# Connect to PostgreSQL
psql postgres

# In PostgreSQL:
CREATE USER connectlink_user WITH PASSWORD 'your_secure_password';
ALTER ROLE connectlink_user WITH CREATEDB;
CREATE DATABASE connectlinkdata OWNER connectlink_user;
GRANT ALL PRIVILEGES ON DATABASE connectlinkdata TO connectlink_user;
\q
```

### Step 5-10: Follow Windows Steps 5-10 Above

(Same process for cloning, virtual environment, dependencies, etc.)

---

## INSTALLATION ON PRODUCTION SERVER

### Pre-Production Considerations

- [ ] Use HTTPS (SSL certificate)
- [ ] Use strong SECRET_KEY
- [ ] Use environment-specific secrets
- [ ] Configure backup automation
- [ ] Set up monitoring
- [ ] Use production web server (Gunicorn)
- [ ] Configure reverse proxy (Nginx)
- [ ] Set up logging

### Production Setup

**1. Install Gunicorn**:
```bash
pip install gunicorn
```

**2. Create Gunicorn Configuration** (`gunicorn_config.py`):
```python
import multiprocessing

workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2
max_requests = 1000
max_requests_jitter = 50
bind = "127.0.0.1:8000"
accesslog = "/var/log/connectlink/access.log"
errorlog = "/var/log/connectlink/error.log"
loglevel = "info"
```

**3. Set Environment to Production**:
```bash
export FLASK_ENV=production
export FLASK_DEBUG=False
```

**4. Use Nginx as Reverse Proxy** (`/etc/nginx/sites-available/connectlink`):
```nginx
upstream connectlink {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name yourdomain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    # SSL Configuration
    ssl_certificate /etc/ssl/certs/yourdomain.crt;
    ssl_certificate_key /etc/ssl/private/yourdomain.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://connectlink;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /path/to/connectlink/static;
        expires 30d;
    }
}
```

**5. Enable Nginx Site**:
```bash
sudo ln -s /etc/nginx/sites-available/connectlink /etc/nginx/sites-enabled/
sudo systemctl restart nginx
```

**6. Create Systemd Service** (`/etc/systemd/system/connectlink.service`):
```ini
[Unit]
Description=ConnectLink Application
After=network.target postgresql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/connectlink
Environment="PATH=/path/to/connectlink/venv/bin"
ExecStart=/path/to/connectlink/venv/bin/gunicorn --config gunicorn_config.py ConnectLink:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**7. Enable and Start Service**:
```bash
sudo systemctl daemon-reload
sudo systemctl enable connectlink
sudo systemctl start connectlink
sudo systemctl status connectlink
```

**8. Verify Application is Running**:
```bash
curl https://yourdomain.com
```

---

## MULTI-BRANCH POS (Shurugwi + Chegutu)

The hardware POS runs as ONE system serving multiple shops. Each shop sees the same
interface and the same shared product catalogue, but its own stock, sales, stock
movements and audit history.

### How it works (in one paragraph)

`products` is the **shared catalogue** (same item, same barcode, same prices in every
shop). The **quantity per shop** lives in `product_stock`. Every sale, stock movement,
product removal and activity entry is stamped with the branch it belongs to, and every
POS screen and report is filtered by the branch held in the **session** — never by
anything the browser sends. `products.stock` is a maintained total across all branches
(it is what the procurement picker and the Finance balance sheet read), so never edit
it by hand: use the stock helpers, which keep it in step.

### Environment variables — SET THESE BEFORE GO-LIVE

The branch codes are **credentials, not labels**: whoever knows a branch's code can open
that shop's till. The shipped defaults are placeholders. Set these in the Render
environment and rotate them periodically:

| Variable | Purpose | Default (CHANGE IT) |
|---|---|---|
| `BRANCH_SHURUGWI_CODE` | Opens the Shurugwi till | `shurugwi01` |
| `BRANCH_CHEGUTU_CODE` | Opens the Chegutu till | `chegutu01` |
| `POS_ALL_BRANCHES_CODE` | Opens the read-only **All Branches** view | `conlink01owner01` |

If a variable is absent the built-in default is used, so a missing value fails **open**.
Always set all three explicitly.

Also worth setting (pre-existing behaviour, unchanged):

| Variable | Purpose | Default |
|---|---|---|
| `TRANSACTION_REVERT_PIN` | PIN required to revert a sale | `Conlink01Admin011235` |
| `PROCUREMENT_DELETE_PASSCODE` | Passcode to delete a requisition | `conlink01admin01` |

### Roles

* **A shop's staff** know only their own branch code. They cannot open another shop
  even if they pick it in the dropdown — the code check is what authorises the branch.
* **Owners** know both branch codes plus the owner code, so they can move between shops
  and open the consolidated view. No per-user branch permissions are needed.
* **All Branches is read-only.** Sales, stock changes, transfers and both inventory
  wipes are refused server-side (`403 read_only`), not merely hidden in the UI.

### Go-live checklist

1. Set the three branch codes in the environment (and rotate them from the defaults).
2. Deploy and confirm BOTH of these lines in the boot log:
   ```
   [ok] Branch schema ready: SHU backfilled -> transactions(+N), ...
   [ok] product_stock ready (pre-branch rows seeded to SHU: N; 0 on every later boot)
   ```
   The first run seeds Chegutu as branch 2 and moves all existing stock/history to
   Shurugwi (the shop that was live first). **`0` on a later boot is correct, not a
   failure** — only products that pre-date per-branch stock can be seeded, and only
   once. A number other than 0 every deploy means the guard described under
   *An item this shop never stocked* below has been lost.
3. **Confirm the environment variables took effect.** Sign in as an admin and open
   ```
   /api/branch-health
   ```
   It answers "is everything set?" without ever showing a code. You want:
   * `env_check` — all three flags **false** (a `true` means that variable did NOT
     take effect and the shipped default is still in use — almost always a typo),
   * `problem_count` — **0**,
   * `branches` — Shurugwi and Chegutu, both `active`.

   `problems` also reports any row that has no branch yet; such rows would be
   invisible inside a branch view, so it must stay empty.
4. **Rehearse on Shurugwi data before Chegutu opens**: ring one sale, add stock,
   open the Audit Report, print a receipt, and make one small transfer.
5. Check that the POS top bar shows the right branch name, and that a receipt prints
   it (e.g. "Shurugwi Branch").

> **First boot is slower than usual.** The schema migration (branches, per-branch
> stock, backfill) runs on the first request after a deploy, not at import, so the
> first page load can take noticeably longer. That is expected — watch the log for
> the two `[ok]` lines above.

### Behaviour worth knowing

* **Logging in** — the Hardware POS card needs username, password, **branch** and the
  **branch code**. Five wrong codes locks that user's code step for 15 minutes.
* **Switching branch** — the branch chip in the POS top bar switches at any time
  (from any branch, including out of the read-only view). **The cart is cleared** so a
  sale can never span two shops.
* **Transfers** — Inventory → *Transfer Stock*, or the **Transfer** button on any
  inventory row. Stock can only leave the branch you are working in, so nobody can
  drain another shop. Both sides appear in each shop's audit report.
* **Wipes** — *Remove All Items & History* and *Clear All Transactions* are
  **branch-scoped**. They clear the shop you are in, and *cannot* touch the other shop.
* **A session with no branch is not a branch.** Signing in on the **Hardware POS card**
  (username, password, branch, branch code), or the chip's *Switch branch*, is what *chooses*
  a shop. Any other way in — the portal `/login` page also drops a hardware user straight on
  the POS — leaves the session with **no branch chosen**: the till opens with the branch
  prompt (which cannot be dismissed) and loads no catalogue, and the server refuses every
  stock or money change until a branch and its code are supplied. Reads still fall back to
  Shurugwi so nothing becomes invisible, and queued offline sales/laybys are *parked*, never
  counted as failed attempts. This replaced a fallback that *named* such a session Shurugwi,
  which is how one shop's stock came to be read from, and filed against, the other shop.
* **The till shows this branch's own items.** An item this branch has **never** stocked is
  hidden from the sale screen (the catalogue is shared, so this is what keeps one shop's
  list out of the other shop's till). An item this branch *does* stock but is out of today
  keeps its card and reads "Out of stock", so a cashier can still say "we stock it, we're
  out". The Inventory tab now lists this branch's own stock (see the next bullet); the audit
  report still reaches every product, and **Add Stock** puts an item back on the till.
* **The Inventory tab is this branch's own stock.** The table, the metric cards above it and
  the Excel/PDF exports that follow it list only the items this branch carries — an item it
  has never stocked is not a row here. Giving such an item a branch row is what puts it back
  on the till (**Add Stock** on the audit report, a transfer in, or an upload). Nothing is
  lost by it: those products are still offered wherever a product is chosen by name — the
  **Add Product** form's name hints (a name this branch has never stocked is marked
  *"already in the catalogue at another branch - use this exact name"*) and the **Upload New
  Stock** template's *Product Names* sheet both list the whole catalogue — so an item created
  at another branch can still be found here and given a row. A search that only matches the
  other branch's item says exactly that, and names those two ways in. The read-only All
  Branches view is unchanged: every line there is the company's own.
* **Stock shown** — on a real branch every figure is that branch's. On the read-only
  All Branches view, stock figures are the company total. **Add Stock** and **Subtract**
  always re-read the figure from the server as they open (and correct the row, grid and
  metrics to match), and if the till is showing the catalogue it saved on the device, a
  banner says so and gives the time it was saved.

### An item this shop never stocked (phantom `product_stock` rows)

**Symptom.** A product created at Chegutu — a speaker nobody had ever sent to Shurugwi —
appeared in Shurugwi's till and inventory carrying Chegutu's quantity, and company-wide
totals came out **doubled** (the same units counted in both shops).

**Cause.** Two defects in the boot seeder in `ConnectLink.py` (`ensure_branches_schema`):

1. The seeder hands every product with no Shurugwi `product_stock` row a row of its own,
   and takes the quantity from `products.stock` — which is the **company** total — as if
   Shurugwi had received it.
2. It had **no per-database guard**. `_ensure_db_initialized()`'s "already ran" flag is
   per *worker*, not per database, and every Render deploy recycles the worker, so the
   `INSERT ... SELECT` re-ran on **every boot** and re-gifted a row to each product that
   had none — including every item Chegutu added after the first deploy.

The row then had two effects, because `stocked_here` (see `run1hardware`) is simply
*"does this branch have a `product_stock` row at all"*: the item **showed stock** it had
never been sent, and the row **stopped the till hiding it**, which is exactly the rule
that is supposed to keep one shop's catalogue out of the other shop's sale screen.

**Fix.** The seed now only assigns stock to a product that has **no branch row at all**
(a product already carrying a row belongs to the shop that created it) and is guarded so
it runs once ever, not once per boot:

```sql
INSERT INTO product_stock (product_id, branch_id, stock, min_stock_level)
SELECT p.id, %s, COALESCE(p.stock, 0), COALESCE(p.min_stock_level, 10)
FROM products p
WHERE NOT EXISTS (SELECT 1 FROM product_stock ps WHERE ps.product_id = p.id)
ON CONFLICT (product_id, branch_id) DO NOTHING
```

`products.stock` is then re-derived as `SUM(product_stock.stock)`, so it keeps meaning
"total across all branches". The guard is what makes the seed idempotent; without it the
COUNT in the boot log climbs on every deploy.

**Repairing a database that already has phantom rows.** The fix stops new ones but cannot
know which existing rows were earned, so use the repair script. It is **read-only unless
you pass `--apply`**:

```bash
python _branch_stock_phantom.py            # report only - lists candidates, writes nothing
python _branch_stock_phantom.py --apply    # deletes them, backs up first
```

A row is only deleted when **all** of the following hold, so a genuinely earned row is
never taken away:

* the product is stocked by at least one **other** branch,
* Shurugwi has **no** `stock_additions` for it (no delivery was ever recorded there),
* it has **no** FIFO layer other than the boot-generated `opening`/`backfill` ones
  (i.e. nobody has bought or costed it at Shurugwi),
* Shurugwi has **no** sale of it.

If an older database lacks `branch_id`/`voided` columns the checks degrade to flagging
*fewer* rows, never more. `--apply` copies what it is about to remove into
`product_stock_repair_backup` (and FIFO layers into `stock_lots_repair_backup`), then
re-derives `products.stock`. Before and after figures for both shops are printed.

**Verifying the rules that keep this from coming back.** `python _check_inventory_stocked_only.py`
reads the page and the app and asserts, with no database and no browser, that the Inventory
table narrows to the items this branch has a `product_stock` row for (and that nothing narrows
the catalogue *itself*), that the metrics and both exports follow the table, that an empty
table names the way in, and that the Add Product name hints and the upload template's *Product
Names* sheet still carry **every** catalogue name; it then drives a real browser against a
stand-in POS API — a branch stocking 2 of 3 items, a search that only matches the other shop's
item, the name hints and the read-only All Branches view. It writes
`_check_inventory_stocked_only_out.txt`.

### A reverted sale still counted as a sale (the audit report)

**Symptom.** The audit showed a sale going out on the 5th and the same goods coming back as an
*addition* funded by **VOID** on the 6th — for a sale Transaction History already showed as
**reverted**, one that sold nothing. *Sale Reductions* was therefore inflated by the returned
quantity, on top of the phantom *Additions* line beside it.

**Cause.** Two defects that only show together:

1. Reverting a sale (`/api/transactions/<id>/revert`) and cancelling a layby do **two** things:
   they write the goods back as a `stock_additions` row (`funding_source` *VOID* or
   *LAYBY_CANCEL*), **and** they *soft*-delete the sale — so the `transaction_items` row stays
   put. The report reads its sales from `transaction_items` on purpose (it is the only source
   that covers every sale, including older ones never mirrored into `stock_reductions`), so the
   reverted sale was still read as a sale.
2. Nothing removed the goods the revert had put back, so one reversal was counted twice: once
   as an outflow and once as an inflow.

**Fix.** `_drop_finished_reversals()` in `ConnectLink.py` drops a reversal's **two** halves
together, and only when **both** fall inside the reported window:

* the voided sale line is matched to the restore its revert wrote back — same branch, same
  product, same quantity, and the **same moment** (a revert stamps `added_at` and `voided_at`
  with one `CURRENT_TIMESTAMP`; a cancellation uses one `now` for both), so the halves of one
  reversal are recognised without guesswork;
* both then leave the movements list, the per-product columns, the period totals and the
  summary — one consistent story, instead of a reduction column that disagrees with the rows.

The two must move together: opening stock is *derived* as `closing − additions + reductions`,
so dropping either half alone would shift it by the returned quantity. A **lone** half is
deliberately left in place — a sale reverted in a *later* period really did take stock off the
shelf during this one, and a revert whose sale was *earlier* really did put goods back. A pair
that cannot be matched (an older row with no moment to pair on) is left exactly as it was
found, so a missed match degrades to the old behaviour and never to a drifting opening figure.

Nothing is hidden by this: `/api/transactions/voided` still lists every reverted sale with who
reverted it and when, so the voided-sales sheet remains where a reversal is read.

### A quantity on screen that is not the server's (the till's saved copy)

**Symptom.** The Inventory tab showed **26** for a product whose branch really held **8**.
Removing 23 was refused — *"Shurugwi has 8 unit(s) ... so 23 cannot be removed"* — which is
the right answer to the wrong screen: the till should never have said 26 in the first place.

**Cause.** The figure was the copy of the catalogue **this device saved** (the till could not
reach the server when it loaded, so it replayed its own copy), and three things made that
copy look like the truth:

1. A catalogue load that failed **for any reason** left the previous figures on screen with
   no notice at all — only a *rejected* request set the banner, and a `500`/`502`, or a
   `200` that was not a product list, went entirely unmentioned.
2. The "live" per-product probe that **Add Stock** and **Subtract** take before opening was
   itself answered out of that saved copy: the wrapper matched request URLs by **substring**
   (`/api/products` is *in* `/api/products/7`), so a probe was treated as cacheable and handed
   back the old figure as if the server had just confirmed it.
3. Nothing re-read the catalogue when the connection came back, so the saved figures stayed
   on screen — and in the Inventory table — for the rest of the session.

**Fix.** The till now knows, and says, exactly how fresh its figures are:

* **Only the catalogue endpoints are ever saved or replayed** (`/api/products`,
  `/api/categories`, `/api/branches`, `/api/check-auth`), matched on the **whole** path. A
  per-product probe and a barcode lookup are never served from the saved copy, and any such
  entry an older build already saved is **pruned** the next time the page loads.
* A replayed answer is **tagged** (`X-ConnectLink-Saved-Copy`), and a probe refuses a tagged
  answer exactly as if the request had failed — so a figure is only called live when the
  server really answered.
* A load that fails turns the warning banner on and the Inventory header reads **"Figures NOT
  confirmed by the server"**, instead of silently keeping yesterday's numbers. A live load
  hides the banner and the header reads **"Figures confirmed by the server at HH:MM:SS"**.
* **Add Stock and Subtract say when the figure in front of them is not live**, and neither
  refuses locally on it: the server decides and answers with the real quantity. An addition
  is refused outright on an unconfirmed base, because an addition *writes* the branch's new
  absolute total — adding 5 to a saved "26" while the branch holds 8 would book 31.
* The catalogue is re-read **when the connection returns**, when the tab comes back to the
  foreground, on the 30-second sweep (only while the screen is known to be stale), and
  **every time the Inventory page is opened** — the page where quantities are read and
  corrected.

**Verifying it.** `python _check_pos_freshness.py` checks the rules statically, and
`python _pos_freshness_browser.py` drives a real browser (Playwright) against a throw-away
stub server with a saved copy of "26" while the server holds 8 — including the refusal and
the refresh when the Inventory page is opened. Neither touches the live database.

### A sale rung offline that took more than the shelf held

**What happens.** A till with no connection sells from the catalogue it saved on the
device, so it can ring a sale against a quantity the shop has since lost (the same
8-vs-26 gap as above, but at the till instead of on the Inventory tab). By then the money
is in the drawer, so the sale is **never refused**: it is queued on the device
(`client_ref`) and replayed by `/api/transactions/sync`, which is idempotent, so the shop
is charged once however often the till retries.

**What the shop is told, and when.**

| When | Where | What it says |
|---|---|---|
| Before the money is taken | The **Order Confirmation** dialog (and the page banner) | *Stock on this screen is not confirmed by the server…* — and that the sale is still taken |
| As the sale is saved | The till's toast | *No connection – sale saved on this device…*, with the time the stock copy was saved |
| The moment it syncs | The till's toast | *This branch was already short: &lt;item&gt; now -4…* — naming the product and the figure |

The sync reply carries a `warning` for each affected sale plus an `oversold` count for the
batch, so the till says it in the operator's own words instead of leaving a minus quantity
to be discovered later. Every sync also records the count in the audit log (*Offline sync:
N sale(s) synced, … , M took more than the shelf held*).

**Why the till is allowed to do this at all.** Offline selling is deliberate and stays:
the alternative turns every dropped link into "the till cannot take money". What is not
allowed is doing it *silently* — the three notices above are the price of that choice.

**Finding and fixing the stock.** The same sales are listed by `GET /api/pos/reconciliation`
(an offline sale that left a branch negative is flagged `suspect`), and
`POST /api/pos/reconciliation/reassign` moves a mis-filed sale to the branch that really
rang it. The movement note is deliberately left as `Sale #<number> (offline sync)` — the
exact string the reassign tool matches on — so **never reword it**, or such a sale can no
longer be put right.

**Verifying it.** `python _check_pos_freshness.py` also checks that the sync reply names
the shortfall, that the note the reassign tool matches on is untouched, and that the till
discloses it in the confirmation dialog and when queueing a sale;
`python _pos_freshness_browser.py` opens a real confirmation dialog against the throw-away
stub server and asserts the warning appears on an unconfirmed figure and disappears once
the server has answered. Neither touches the live database.

### A till that has been logged out with sales still on it

**What happens.** Selling and *filing* are separate: the sale is queued on the device with no
login at all, and only the last step — `POST /api/transactions/sync`, the one login-protected
POS route — needs the session. So if a till is logged out (someone pressed **Logout**, or the
browser's storage was cleared) the counter keeps working and the sales keep queueing; they are
simply not filed until somebody logs in once. Nothing is discarded: the batch is refused whole,
with no retry counted against any sale, and it is retried on the next page load, the next
`online` event, the tab coming back, the 30-second sweep, or **Sync now**.

**What the till says.** Not the server's bare *Session not found* — which read, on a busy
counter, as if the money had been lost. It says how much is waiting:

> *3 sales saved on this till – log in once and they file themselves.*

Sales and layby items are counted separately and named together when both are waiting. The
notice is repeated only when the count changes (and at most once a minute), and it is cleared
by the first sync that gets through, so a *second* logout is announced again.

**A lie that is now gone.** The refusal used to add *"Sessions last 6 hours. Please logout and
login again to start a new session."* — false: the session cookie is permanent, so a till that
looked fine yesterday still has its session today. Shops acted on that sentence and went
looking for a login fault that did not exist. The message now reads *"Session not found. Log in
again to continue."*, and the same false claim was removed from the admin page's expiry toast.

**Laybys are held, not parked.** A layby event that meets a dead session used to be marked
`blocked` — i.e. taken out of the retry queue and shown under **needs attention** on the Layby
tab, when all it needed was a login. It is now held like an offline item, and the rest of that
queue is left alone rather than failed item by item.

**What to do about it.** Log in once on that till (any valid user for the same shop) and press
**Sync now** if the chip does not clear within a minute. The queue survives a reload, a
browser restart and days of being offline; it does **not** survive someone clearing the site's
data for that browser, which is also what a "reset" of the till means.

**Verifying it.** `python _check_pos_freshness.py` checks the wording, the counting and that no
retry is burned on a dead session; `python _pos_freshness_browser.py` rings a sale on a real
page against a stub server that answers `401 session_expired`, then answers properly, and
asserts the count is announced, the sale is kept, and it files itself after that one login.
Neither touches the live database.

### The project portal with no connection (read-only, plus contracts)

The portal does **not** queue anything. An edit there is a whole-row update the server judges
(permissions, and whether the branch is read-only), so an offline replay would quietly overwrite
whatever happened in the meantime. With no connection a change is refused, and the page says so
plainly: *"No connection. Nothing was saved and nothing was sent, and nothing has been queued on
this device."*

What the portal **can** do offline is read. The service worker keeps exactly two small buckets:

| Kept | Why |
| --- | --- |
| `get_project_count`, `get_project_months`, `get_project_start_months`, `get_project/<id>`, `/api/projects-page`, `/api/project/<id>/has-gantt` | the project figures the lists are built from, so the projects pages still open with no connection |
| `download_contract/<id>` — every contract that has been downloaded, or saved with **Save for offline** | a contract can still be opened and re-downloaded with no connection |

Each endpoint is matched on the **whole path** (never as a substring), and every saved copy
carries the time it was saved. When a figure comes from the device rather than the server, a bar
at the bottom of the screen says so: *"No connection. The figures on this screen are a copy saved
on this device at HH:MM on D Mon, and may be out of date. Nothing here can be sent or saved."*
The bar goes the moment the server answers again. An endpoint with no saved copy is **refused**
rather than answered with a stale figure, and a money figure — **project over-costs** — is
deliberately *not* on the list at all: a saved copy of it is worse than no answer. The export and
every other route are left exactly as they were.

**Contract copies.** A contract is kept on the device the first time it is downloaded, and the
contract dialog offers **Save for offline** for a copy kept on purpose. A contract opened from
the device also says the server has **no record of that download**, so nobody later wonders why a
client holds a contract the audit log never saw. These copies carry client details, so the same
dialog offers **Delete saved copies**; they are also dropped automatically once 30 are held or
40 MB is reached (oldest first), and **logging out clears them**. They live in that browser
profile's own storage, exactly like the till's queued sales: another machine — or cleared site
data — has none. The figures bucket carries the worker's version in its name, so a deploy simply
replaces it; the **contract** bucket deliberately does not, so a copy somebody asked us to keep is
not thrown away by a deploy — only *Delete saved copies*, the size limit and logging out remove
those.

**Deploying it.** The worker's cache version was bumped, so the first page load after the deploy
replaces the old worker; until a given browser has loaded a page once, it simply has no offline
buckets yet.

**Verifying it.** `python _check_portal_offline.py` checks, with no browser and no database, that
only the named endpoints are replayable (whole-path matches, no money route, no write route),
that nothing is handled but GET, that every copy is stamped with when it was saved, that both
buckets are bounded, and that the page says what it is showing. `python
_portal_offline_browser.py` drives a real Chromium against a stub server: it goes offline,
replays a saved figure (stamped, and announced with its saved time), refuses a figure that was
never saved and the money endpoint, fails a change with "nothing was saved", opens a contract
that has been through once while refusing one that never has, then deletes the copies and checks
that logging out takes the rest.

### Project changes in the audit log

**Every change to a field on a project is now audited, one row per field**, carrying the
name people know the field by, **what it was and what it became**, who did it and when.
Nothing on a project can be changed and leave no trace.

Where it applies (all of these write to the shared `activity_log`):

| Screen / action | What is recorded |
| --- | --- |
| Progress Update (`/update_project`) | Client name, project name, scope, completion status, **Total Bill (USD)**, deposit, deposit date, project start date, months to pay, admin name, work schedule, linked quotation, and every instalment amount, due date and paid date |
| Other Details (`/update_other_details`) | National ID, email, WhatsApp, address, all four next-of-kin fields, completion status, agreement date, project location, duration, late-payment interest, linked quotation |
| Work schedule / Gantt save | The schedule itself ("5 task(s)") and the project start date that follows from it |
| Installment reschedule | One row per due date that actually moved (plus the summary line) |
| Installment / deposit receipt, and the same receipt sent by WhatsApp | The **paid date** being recorded — a money event, so it is audited wherever it happens |
| Instalment variance auto-correct | The instalment amount it rewrote, old → new |
| Automatic completion status | One row per recalculation naming the projects it touched, attributed to **System** — the status is derived from the start date and duration, so nobody "edited" it, but it did change |

How it reads on screen:

* **Activity Log** — each change gets its own line under the description showing the
  field name with the old value in red and the new value in green, so the values are
  visible even though the description above it is truncated to one line. The detail
  modal repeats it as a **From → To** block. Field changes have their own icon and
  colour, and are filterable as *Project Field Changed*.
* **Audit Log** (User Management → Audit Log) — the details column reads
  `Total Bill (USD): 5000 → 6000` instead of a truncated JSON blob.
* **Excel export** of the activity log carries the same description and details.

Two deliberate rules: **formatting is never an edit** (`5000`, `5,000.00` and a stored
`Decimal` are the same money, and a date posted as `2026-10-03` equals the stored
timestamp), and when the previous values cannot be read the change is **not** logged —
a failed read must never invent a change from "(empty)".

**Automatic repairs are audited too.** Three places fix corrupted dates without anyone
editing anything — the startup repair for project 125's instalment due dates, the startup
`72026` → `2026` repair, and the same `72026` repair that runs when the projects list is
opened. Each one now records a row per value changed (`project_data_repaired`, filterable
as *Project Data Repaired*) naming the project, the field and the old → new date, and it is
attributed to **System** because nobody chose it. They are silent only when they change
nothing, which is the normal case.

### Stock reconciliation — repairing stock that was mixed up

Before the offline till stamped the branch a sale was rung in, a sale rung in one shop
could be replayed while the till was sitting on the other, so the quantity came off the
wrong shelf. Two things fix that, and they are separate:

1. **Prevention (automatic, nothing to do).** The cached catalogue is tagged with the
   branch that fetched it and is only ever replayed to that shop; queued offline sales
   record the branch they were rung in; and `/api/transactions/sync` **refuses** a sale
   whose recorded branch disagrees with the session, leaving it on the till and saying
   so. A mis-filed deduction can no longer happen silently.
2. **Repair (manual, only if you need it).** **POS drawer → Stock reconciliation**
   (admin only), or Inventory → *Stock Reconciliation*. The page lists every
   offline-synced sale in the branch — the only sales that can ever have been mis-filed —
   and highlights **negative branch stock**, which is the hard evidence that some sale
   deducted goods the shop never held. Moving a sale returns the quantity to the shop
   that wrongly received it and takes it off the shop that sold it, in one transaction,
   and writes a row to `stock_reconciliation_log`.

Safeguards: you can only move a sale *out of* the branch you are standing in, you must
enter the **destination branch's access code**, the move is refused when the destination
cannot cover the quantity, and offline-synced sales held for another branch are never
aged out of the till's queue (dropping them would lose the money). A move changes the
branch, not the history — the receipt keeps its number and time.

> The tool cannot know which shop a sale was *meant* for: the old queue did not record
> it. It surfaces the candidates and a human confirms the destination.

### Layby (reserve now, pay in instalments)

**Layby** is a fourth payment method in the till, beside Cash / Card / Transfer. Choosing
it opens a form for the **customer name, ID number**, optional phone, a **deposit paid
now**, and a **payment plan** — pick the number of instalments and the amount still due
is spread across them (the last one absorbs the rounding), each with an optional
expected date. The instalments **must add up to the amount still due**; the server
refuses the layby otherwise. Goods leave the branch's shelf at the layby, costed from the
FIFO layers they consumed.

How it hits the books:

* The sale is written with the transaction status **`layby`**, which every existing
  "sales today" figure ignores — the money has not been received.
* **Only instalments actually received are counted, on the day they are received.**
  They are recorded on the **Layby** tab in the sidebar (active/paid-off/cancelled
  filter, balance, plan state and payment history per layby).
* When the balance reaches zero the layby *and* its transaction are released to
  `completed`, so the full sale value lands in the sales reports then.
* **Day-end** excludes layby sales from takings and reports what was kept instead — a
  *Layby kept* tile (net of refunds), a per-cashier line, and a `Layby kept` column in the
  Excel export.
* **Audit report** lists layby items like any other sale, badged **Layby**, with the
  receipt number in the details column.
* **Cancelling** returns the reserved stock to the shelf, voids the sale, and **refunds the
  customer**: the amount defaults to everything collected (lower it to keep a fee) and is
  written as its own refund row, so the layby shows what went back and what was retained.
  Refunds are money paid out at the counter and are reported as such.
* **Reverting the sale closes the layby.** A layby sale reverted from **Transaction
  History** returns the reserved goods to the shelf, so the layby is closed with it: it
  stops counting as active, leaves the default *Active laybys* view, and cannot take
  another instalment or be cancelled again — cancelling it would put the same goods back a
  **second** time. What the customer paid stays on the layby's record, with the reason
  *"its sale was reverted from Transaction History"*, so the shop can refund against
  something visible. A layby left active by a revert performed before this existed is
  closed automatically the next time the Layby tab is opened (never from the read-only
  All Branches view).

Tables `laybys`, `layby_items`, `layby_plan` and `layby_payments` are created
automatically on boot, like the branch schema, so there is no manual migration step.

### Laybys on a till with no connection

A layby **and** its instalments can now be taken with no connection at all, alongside cash
sales:

* The till **mints the layby number itself** (`LAY-YYYYMMDD-XXXXXX`), so the paper the
  customer walks away with is the number the books end up with, and keeps the layby (or
  the instalment) on that device.
* The **Layby tab lists what is waiting** at the top, marked *not yet synced*. An
  instalment can be recorded against a layby that has not reached the server yet — it is
  queued behind it and tied to it by that same number.
* The queue replays automatically when the connection returns, and the drawer's
  *Cloud sync* row counts these alongside queued sales.
* **Nothing is ever thrown away.** An instalment for a layby rung in *another branch* is
  held until that branch is selected again, and anything the server refuses is **parked
  with its reason** on the Layby tab, with *Try again* and *Discard* — a person decides,
  not a retry counter.
* Idempotency comes from the till's own reference on every item, so a retry after a
  dropped reply cannot reserve the goods or take the money twice.
* The till also **holds the reserved stock back from its own figures while a layby is
  still queued** (see *Stock a till has promised but not yet uploaded* below), so two
  tills cannot promise the same unit during an outage.

> **Known limitation (queued *sales*, not laybys).** A layby item is never discarded
> automatically, but the older offline **sales** queue still gives up on a sale the server
> actively refuses after 25 attempts and drops it, which loses that paid sale. Network
> outages do not count towards those attempts (the till does not try while it knows it is
> offline). This is the queue's long-standing policy and is unchanged; say the word and it
> can be parked on screen for a person to decide, exactly like a layby.

### Stock a till has promised but not yet uploaded

A till only knows the stock the *server* last told it. While sales or laybys are sitting
in a queue on that device, the goods have physically gone but the catalogue still shows
them, which is how a shop ends up promising the same last unit twice during an outage.

Each till therefore keeps a small local ledger (`pos_local_holds_v1`, in the browser's own
storage) of **what it has taken but not yet uploaded**:

* A sale holds its basket as soon as it is queued; a layby holds its reserved goods, and a
  queued instalment holds nothing (no goods move).
* The held quantity is **subtracted from the figures on screen** — the product grid, the
  inventory list, the low/out-of-stock figures and the *Out of stock!* / *Not enough
  stock!* checks — so the till cannot sell what it has already promised.
* The hold is released the moment the item reaches the server, the moment it is
  discarded, and if a sale is ever abandoned by the retry counter. Removing a layby from
  the queue releases its goods back into the figures.
* Holds are kept **per branch**, so a sale waiting for Chegutu is never taken off
  Shurugwi's shelves while the till is working in Shurugwi.
* The figures refresh from the server as soon as a sync succeeds, so this is a temporary
  correction, not a second ledger of record.
* **Adding stock** and the *Current Stock* figure in the Add Stock box always use the
  **server's** number, never the held-down one — a hold can never be written back as the
  shop's real stock.

### Printing the layby agreement

Both the *Layby* tab and the *not yet synced* cards carry a **Print agreement** button.
It produces the customer's copy: shop and branch, agreement number and date, the
customer's name, national ID and phone, the reserved goods with quantities and prices
footing to the total, the instalment plan with expected dates and what is paid/part
paid/due, the money position (total, paid, refunded, balance), every instalment received,
the notes, the terms, and signature lines for the customer and the shop.

It prints through the normal receipt path, so the till prints it the same way it prints a
receipt. A layby that has **not reached the server yet** can still be printed — the till
holds the customer, the goods and the plan — and that copy is marked *"this agreement was
written on the till while it had no connection"*. Printing is not restricted to active
laybys: a cancelled one prints with the cancellation reason and any refunds on it.

### Bulk stock upload (Excel) — what it will and will not duplicate

Inventory → *Upload New Stock* is two steps and **writes nothing** until you press
Apply.

* **Exact name match** (trimmed, case-insensitive) against the catalogue → **merged**:
  the quantity is added to that product and its prices updated. No duplicate is created.
* **No exact match but a name at least 72% similar** → raised as a **conflict** with up
  to five candidates and their similarity percentages, and you choose *Add to an existing
  product* or *Create a new product*.
* **Nothing similar** → treated as a new product. Rows for the same new product are
  collapsed into one product before anything is written (quantities summed,
  weighted-average cost, last price wins), so one file cannot create the same product
  twice.
* **Category.** The file's Category is matched case-insensitively against the live
  category list, and anything unrecognised is blanked (the page's default category is
  used instead). When a row matches an existing product **by name but carries a different
  category**, that is raised as a **conflict row** — it shows both categories and you
  choose *Add to the existing category*, *Use the category from my file*
  (`merge_category`, which changes the product's category as well as its stock), or
  *Create a separate product*. Nothing is applied until you decide.
* **The template hands you every name the catalogue already uses.** Its *Product Names*
  sheet is built from the **whole** catalogue, across every branch — so a name another shop
  created is there to pick — and the **Product Name** column now says the rule out loud:
  *"Pick the name the catalogue already uses to add stock to that product. A name that is
  not on the list creates a NEW product, so only type one when the item really is new."*
  The Inventory table lists only this branch's own stock, so this sheet (and the Add Product
  form's name hints) is where the other branches' names are found.
* There is no re-check between *Check File* and *Apply*, so do not leave a checked file
  sitting while someone else adds the same product.

---

## CONFIGURATION

### Environment Variables

**Development** (`.env`):
```
FLASK_ENV=development
DEBUG=True
FLASK_DEBUG=True
SECRET_KEY=dev-key-only-for-development-not-secure
DATABASE_URL=postgresql://user:pass@localhost/connectlinkdata
```

**Production** (in CI/CD or server environment):
```
FLASK_ENV=production
DEBUG=False
FLASK_DEBUG=False
SECRET_KEY=<generate-with: python -c "import secrets; print(secrets.token_hex(32))">
DATABASE_URL=postgresql://user:pass@prod-db-server/connectlinkdata
GEMINI_API_KEY=<actual-api-key>
WHATSAPP_API_TOKEN=<actual-token>
```

### Generate Secure SECRET_KEY

```python
# Python
import secrets
print(secrets.token_hex(32))
```

### Configure Database Connection

**Connection String Format**:
```
postgresql://username:password@hostname:port/database_name
```

**Examples**:
```
# Local development
postgresql://connectlink_user:mypassword@localhost:5432/connectlinkdata

# Production
postgresql://prod_user:secure_password@db.prod.example.com:5432/connectlinkdata
```

### Configure API Keys

**1. Google Gemini API**:
   - Go to: https://makersuite.google.com/app/apikey
   - Create new API key
   - Copy to `.env` as `GEMINI_API_KEY`

**2. WhatsApp Business API**:
   - Register at: https://www.whatsapp.com/business/
   - Get API token
   - Get Phone ID
   - Copy to `.env`

**3. (Optional) SendGrid Email**:
   - Register at: https://sendgrid.com
   - Get API key
   - Copy to `.env`

---

## DATABASE MANAGEMENT

### Backup Database

**Full Backup**:
```bash
pg_dump -U connectlink_user connectlinkdata > backup_$(date +%Y%m%d_%H%M%S).sql
```

**Compressed Backup**:
```bash
pg_dump -U connectlink_user connectlinkdata | gzip > backup_$(date +%Y%m%d).sql.gz
```

**Scheduled Backup (Cron - Linux/macOS)**:
```bash
# Edit crontab
crontab -e

# Add this line (backup daily at 2 AM)
0 2 * * * pg_dump -U connectlink_user connectlinkdata | gzip > /backups/connectlink_$(date +\%Y\%m\%d).sql.gz
```

### Restore Database

**Full Restore**:
```bash
psql -U connectlink_user connectlinkdata < backup_20260415.sql
```

**From Compressed Backup**:
```bash
gunzip -c backup_20260415.sql.gz | psql -U connectlink_user connectlinkdata
```

### Database Optimization

**Analyze Tables** (improves query performance):
```bash
psql -U connectlink_user connectlinkdata -c "ANALYZE;"
```

**Vacuum Database** (removes dead tuples):
```bash
psql -U connectlink_user connectlinkdata -c "VACUUM ANALYZE;"
```

**Add Indexes** (speed up frequent queries):
```sql
CREATE INDEX idx_projects_status ON connectlinkdatabase(status);
CREATE INDEX idx_products_category ON connectlinkinventory(category);
CREATE INDEX idx_transactions_date ON connectlinktransactions(date);
CREATE INDEX idx_payments_status ON payments(status);
```

### Verify Database Health

```bash
# Check database size
psql -U connectlink_user connectlinkdata -c "SELECT pg_size_pretty(pg_database_size('connectlinkdata'));"

# List all tables
psql -U connectlink_user connectlinkdata -c "\dt"

# Check table sizes
psql -U connectlink_user connectlinkdata -c "SELECT table_name, pg_size_pretty(pg_total_relation_size(quote_ident(table_name))) FROM information_schema.tables WHERE table_schema = 'public' ORDER BY pg_total_relation_size(quote_ident(table_name)) DESC;"
```

---

## BACKUP & RECOVERY

### Automated Backup Strategy

**Daily Backups**:
```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backups/connectlink"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/connectlink_$TIMESTAMP.sql.gz"

# Create backup directory if not exists
mkdir -p $BACKUP_DIR

# Perform backup
pg_dump -U connectlink_user connectlinkdata | gzip > $BACKUP_FILE

# Keep only last 30 days of backups
find $BACKUP_DIR -name "connectlink_*.sql.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_FILE"
```

**Make executable**:
```bash
chmod +x backup.sh
```

**Add to crontab**:
```bash
# Daily at 2 AM
0 2 * * * /path/to/backup.sh >> /var/log/connectlink_backup.log 2>&1

# Multiple times per day (every 6 hours)
0 */6 * * * /path/to/backup.sh >> /var/log/connectlink_backup.log 2>&1
```

### Disaster Recovery Plan

**Step 1: Assessment**
- Identify what failed (database, app, server)
- Determine data loss tolerance
- Choose appropriate backup point

**Step 2: Restore from Backup**
```bash
# Stop application
sudo systemctl stop connectlink

# Restore database
psql -U connectlink_user connectlinkdata < /backups/connectlink_20260415_020000.sql

# Verify restore
psql -U connectlink_user connectlinkdata -c "SELECT COUNT(*) FROM connectlinkdatabase;"

# Restart application
sudo systemctl start connectlink
```

**Step 3: Verification**
- Test login
- Check recent data
- Verify all functionality
- Monitor logs for errors

**Step 4: Communication**
- Notify users of downtime
- Provide status updates
- Confirm service restoration

---

## MONITORING & MAINTENANCE

### Application Monitoring

**Check Application Status**:
```bash
# Systemd service status
sudo systemctl status connectlink

# Check if listening on port
sudo netstat -tulpn | grep 8000
# or
sudo ss -tulpn | grep 8000
```

**Monitor Application Logs**:
```bash
# View recent logs
sudo tail -100 /var/log/connectlink/error.log
sudo tail -100 /var/log/connectlink/access.log

# Follow logs in real-time
sudo tail -f /var/log/connectlink/error.log
```

### Database Monitoring

**Monitor Database Connections**:
```sql
SELECT datname, count(*) as connections FROM pg_stat_activity GROUP BY datname;
```

**Monitor Slow Queries** (enable slow query logging):
```sql
ALTER SYSTEM SET log_min_duration_statement = 1000;  -- Log queries > 1000ms
SELECT pg_reload_conf();
```

**Check Database Activity**:
```sql
SELECT pid, usename, application_name, state, query FROM pg_stat_activity;
```

### System Monitoring

**CPU & Memory Usage**:
```bash
# Overall system
free -h
top -b -n 1

# PostgreSQL process
ps aux | grep postgres
```

**Disk Space**:
```bash
df -h
du -sh /path/to/connectlink

# PostgreSQL logs
du -sh /var/log/postgresql/
```

### Automated Health Checks

**Create Health Check Script** (`health_check.sh`):
```bash
#!/bin/bash

# Check application
if ! curl -s http://localhost:5000/health > /dev/null; then
    echo "Application is down!"
    sudo systemctl restart connectlink
fi

# Check database
if ! psql -U connectlink_user connectlinkdata -c "SELECT 1" > /dev/null 2>&1; then
    echo "Database is down!"
    sudo systemctl restart postgresql
fi

echo "Health check passed: $(date)"
```

**Run Hourly**:
```bash
# Add to crontab
0 * * * * /path/to/health_check.sh >> /var/log/health_check.log 2>&1
```

### Maintenance Schedule

**Daily**:
- [ ] Check error logs
- [ ] Monitor disk usage
- [ ] Verify backups completed
- [ ] Check database performance

**Weekly**:
- [ ] Review security updates
- [ ] Analyze slowest queries
- [ ] Test backup restoration
- [ ] Check application metrics

**Monthly**:
- [ ] Database optimization (VACUUM, ANALYZE)
- [ ] Security audit
- [ ] Performance tuning
- [ ] Update dependencies
- [ ] Plan capacity

**Quarterly**:
- [ ] Major updates/patches
- [ ] Security review
- [ ] Disaster recovery drill
- [ ] Documentation updates

---

## TROUBLESHOOTING

### Application Won't Start

**Error: "Address already in use"**
```bash
# Find process using port 5000
sudo lsof -i :5000
# or
sudo netstat -tulpn | grep 5000

# Kill the process
sudo kill -9 <PID>
```

**Error: "ModuleNotFoundError: No module named..."**
```bash
# Verify virtual environment is activated
which python
# Should show: /path/to/connectlink/venv/bin/python

# If not, activate it
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate  # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

**Error: "Database connection refused"**
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Start PostgreSQL if stopped
sudo systemctl start postgresql

# Verify connection string in .env
# Format: postgresql://user:password@host:port/database
psql -U connectlink_user -h localhost -d connectlinkdata
```

### Multi-Branch: one shop's item shows up in the other shop's till

**A product only Chegutu ever had appears in Shurugwi (often with Chegutu's quantity),
and totals look doubled.**

That is a phantom `product_stock` row: Shurugwi carries a row for an item it never
received. Check with the read-only repair script first — no writes, safe to run against
production:

```bash
python _branch_stock_phantom.py
```

It lists each candidate with the evidence for and against (other branches stocking it,
Shurugwi deliveries, FIFO layers, sales). If the list is exactly the items you expect,
clear it:

```bash
python _branch_stock_phantom.py --apply
```

Then reload the POS — the item disappears from Shurugwi's till and from its Inventory tab
(the item itself is untouched: it is still in the shared catalogue, so it is still offered
by name on the Add Product form and in the upload template), and the company totals fall
back to reality. Both tables it touches are backed up first (`product_stock_repair_backup`,
`stock_lots_repair_backup`). Full background: see *An item this shop never stocked* under
**MULTI-BRANCH POS**.

**If the phantom rows keep coming back after a deploy**, the boot seeder's guard has been
lost. Confirm the boot log prints `pre-branch rows seeded to SHU: 0` on the second and
later boots; anything else means `ensure_branches_schema`'s `INSERT ... SELECT` is running
unguarded again.

### Multi-Branch: a shop's stock figure is higher than the server's (the saved copy)

**The Inventory tab shows 26; removing 23 is refused and the refusal says the branch has 8.
Both are "correct" — the screen was showing the catalogue this device had saved.**

The figure is not the server's, so nothing on screen may be acted on until the till has
re-read it. Check, in this order:

1. Is the orange banner up (*"Showing the figures saved on this device"*)? That says the
   loaded figures are the saved copy, and gives the time it was taken. The Inventory header
   adds *"Figures NOT confirmed by the server"*.
2. Press **Refresh** (or pick the Inventory page, which re-reads the catalogue whenever it is
   opened). The header should change to *"Figures confirmed by the server at HH:MM:SS"* and
   the banner disappear. If a figure then changes, the old one was the saved copy.
3. If it will not reach the server, the till is offline: it is working from the copy it
   saved. Sales still go through and queue; the quantities will correct themselves as soon
   as the connection returns (the till re-reads the catalogue the moment it does).
4. If `/api/products` is answering with an error (a `500`/`502`, or an HTML error page), the
   till now says so — *"Could not load the catalogue (HTTP 500) - the figures on screen are
   not live."* — and keeps the figures **flagged as not confirmed**. Check the Render logs
   and the database connection rather than trusting the numbers.

Add Stock and Subtract never block a correction on a figure the till cannot confirm: they
send the request, and the server answers with its own live quantity. What the till will
**not** do is *add* stock on top of an unconfirmed figure, because an addition writes the
branch's new absolute total. Full background: see *A quantity on screen that is not the
server's* under **MULTI-BRANCH POS**.

### Database Issues

**Error: "Database does not exist"**
```bash
# Create database
psql -U postgres
CREATE DATABASE connectlinkdata OWNER connectlink_user;
\q

# Initialize tables
python ConnectLink.py  # Run application to create tables
```

**Error: "Permission denied for schema public"**
```sql
GRANT ALL PRIVILEGES ON SCHEMA public TO connectlink_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO connectlink_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO connectlink_user;
```

**Database Growing Too Large**
```sql
-- Check table sizes
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) FROM pg_tables ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Clean up old data
DELETE FROM transactions WHERE date < NOW() - INTERVAL '1 year';
VACUUM ANALYZE;
```

### API Integration Issues

**WhatsApp Messages Not Sending**
```python
# Test WhatsApp connection
from src.communication import WhatsAppService
service = WhatsAppService()
result = service.test_connection()
print(result)
```

**Gemini API Not Responding**
- Verify API key is correct
- Check quota limits
- Test API directly:
```bash
curl -X POST https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key=YOUR_API_KEY \
  -H "Content-Type: application/json" \
  -d '{"contents":[{"parts":[{"text":"Hello"}]}]}'
```

### Performance Issues

**Slow Queries**
```sql
-- Enable query logging
ALTER SYSTEM SET log_statement = 'all';
SELECT pg_reload_conf();

-- Check slow queries
SELECT query, calls, mean_time FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;
```

**High Memory Usage**
```bash
# Restart application
sudo systemctl restart connectlink

# Check for memory leaks
ps aux | grep connectlink
# End process if >50% memory
sudo kill -9 <PID>
sudo systemctl start connectlink
```

### Render Worker Timeouts / OOM ("WORKER TIMEOUT ... SIGKILL ... out of memory")

**Symptoms**: repeated `[CRITICAL] WORKER TIMEOUT` → `Worker ... was sent SIGKILL! Perhaps out of memory?`, workers cycling, and `No open ports detected` during deploys.

**Causes & fixes**:
1. **Too many gunicorn workers on a small (free 512MB) instance.** Every worker imports the whole app (pandas/numpy/seaborn/weasyprint/google-genai) and, previously, ran a full DB schema migration at import. Use 1 worker + threads. The repo now ships a `Procfile`:
   ```
   web: gunicorn ConnectLink:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 180 --graceful-timeout 60 --max-requests 500 --max-requests-jitter 50
   ```
   If your Render service uses a dashboard "Start Command" instead of the Procfile, update it to the same command (Render uses the Procfile's `web` line when present).
2. **Gunicorn default timeout is 30s** — too short for US Postgres latency + dashboard polling. `--timeout 180` fixes it.
3. **DB schema init ran at module import** (before the worker bound the port) → Render's port scan timed out and every worker repeated the migration. Fixed in `ConnectLink.py`: schema init (`initialize_database_tables()` + `migrate_product_categories()`) now runs **lazily on the first request** (guarded by a lock), so the worker binds the port immediately and migration happens once.
4. **Heavy imports at module load** still slow boot and eat memory even with 1 worker. Done in `ConnectLink.py`: removed the unused `import seaborn as sns`, and made `google.generativeai` (grpcio/protobuf) and `ai_classifier` (fuzzywuzzy) **lazy imports** — they only load when the AI features are actually used, not at every worker boot. (`weasyprint` is still imported at module level because PDF generation uses it widely.)

---

## UPGRADE PROCEDURES

### Before Upgrade

- [ ] Backup database
- [ ] Backup configuration files
- [ ] Note current version
- [ ] Check upgrade warnings
- [ ] Schedule downtime if needed

### Upgrade Steps

**Step 1: Stop Application**
```bash
sudo systemctl stop connectlink
```

**Step 2: Backup Current Version**
```bash
cp -r /path/to/connectlink /path/to/connectlink_backup_v2.0
```

**Step 3: Pull Latest Code**
```bash
cd /path/to/connectlink
git fetch origin
git checkout main
git pull origin main
```

**Step 4: Update Dependencies**
```bash
source venv/bin/activate
pip install -r requirements.txt --upgrade
```

**Step 5: Run Database Migrations** (if any)
```bash
python manage.py db upgrade
```

**Step 6: Test Application Locally** (development)
```bash
python ConnectLink.py
# Test in browser at http://localhost:5000
```

**Step 7: Restart Service** (production)
```bash
sudo systemctl start connectlink
sudo systemctl status connectlink
```

**Step 8: Verify Upgrade**
```bash
# Check logs
sudo tail -50 /var/log/connectlink/error.log

# Test functionality
curl https://yourdomain.com
```

### Rollback Procedure (if needed)

**Step 1: Stop Application**
```bash
sudo systemctl stop connectlink
```

**Step 2: Restore Previous Version**
```bash
rm -rf /path/to/connectlink
cp -r /path/to/connectlink_backup_v2.0 /path/to/connectlink
```

**Step 3: Restore Virtual Environment**
```bash
rm -rf /path/to/connectlink/venv
python3 -m venv /path/to/connectlink/venv
source /path/to/connectlink/venv/bin/activate
pip install -r requirements.txt
```

**Step 4: Restart Service**
```bash
sudo systemctl start connectlink
```

---

## Version History

| Version | Release Date | Key Changes |
|---------|--------------|-------------|
| 2.0 | April 2026 | Full system release with all modules |
| 1.5 | January 2026 | Added AI classification, WhatsApp integration |
| 1.0 | October 2025 | Initial release |

---

## Support & Resources

- **Documentation**: See README_COMPLETE_SYSTEM.md
- **Quick Reference**: See QUICK_REFERENCE.md
- **Architecture**: See SYSTEM_ARCHITECTURE.md
- **Email Support**: support@connectlink.co.zw
- **Emergency Hotline**: +1234567890
- **Issue Tracker**: https://github.com/your/repo/issues

---

## Changelog

**October 2026 — the Inventory tab lists only what this branch carries**
- ✅ **The Inventory table is this shop's own stock, and nothing else.** It used to list the
  whole shared catalogue, with the other shop's items reading *"Not stocked here"* — behind
  an opt-in *"Stocked in this branch only"* switch that was **unticked by default**, so in
  practice one shop's list filled the other shop's Inventory. The switch is **gone** and the
  table always narrows to the items this branch has a `product_stock` row for: the table,
  the metric cards above it, and the Excel and PDF exports (which follow the table).
- ✅ **An empty table says why, and names the way in.** A search that only matches an item
  the *other* shop carries reads *"1 item(s) match this search in the shared catalogue, but
  this branch does not stock them. Use Upload New Stock - or Add Product with that exact
  name - to start selling one here."*, and a genuinely empty branch reads *"Nothing is
  stocked in this branch yet. Add a product, or upload stock for an item the catalogue
  already has."*
- ✅ **Every name is still offered, so nothing gets entered twice.** The catalogue itself was
  never touched: the removed switch narrowed a *view* only. Both places where a product is
  chosen **by name** still list every name in the catalogue — the **Add Product** form's
  name hints, which now mark a name this branch has never stocked *"already in the catalogue
  at another branch - use this exact name"*, and the **Upload New Stock** template's
  *Product Names* sheet, whose **Product Name** cell now prompts *"Pick the name the
  catalogue already uses to add stock to that product. A name that is not on the list
  creates a NEW product, so only type one when the item really is new."*
- ✅ The consolidated **All Branches** view is unchanged: every product is listed with
  company totals, because the server there reports every item as the company's own.
- Verified without a database: `python _check_inventory_stocked_only.py` — the switch has
  really gone (page, wiring and markup), the filter narrows, the empty note, both exports
  following the table, the hints and the template pick-list still carrying every name, then
  a real browser against a stand-in POS API (a branch stocking 2 of 3 items, the search
  matching only the other shop's item, the name hints, and All Branches).

**October 2026 — the till never trusts a stock figure it cannot confirm**
- ✅ **A screen that is showing the copy this device saved now says so, and stops pretending.**
  A catalogue load that failed for *any* reason used to leave the previous figures in place
  with no notice (only a rejected request set the banner; a `500`/`502`, or a `200` that was
  not a product list, went unmentioned). Any such load now turns the banner on, and the
  Inventory header reads **"Figures NOT confirmed by the server"** instead of quietly showing
  yesterday's numbers.
- ✅ **The "live" probe behind Add Stock and Subtract is a real probe.** It was being answered
  out of the same saved copy — request URLs were matched by substring, and `/api/products`
  appears in `/api/products/7` — so a probe "confirmed" a figure the server had since moved.
  Only the catalogue endpoints are saved or replayed now, matched on the whole path, any
  saved probe entry is pruned on load, and a replayed answer is tagged
  (`X-ConnectLink-Saved-Copy`) so a probe can refuse it exactly as if the request had failed.
- ✅ **Both boxes say when their figure is not live, and neither refuses a correction on it.**
  A removal on an unconfirmed figure went through the local "only N in stock" check, which is
  what made *"it says 26, but 23 cannot be removed"* so confusing. The server now judges it
  and answers with the real quantity. An **addition** is refused on an unconfirmed base,
  because an addition writes the branch's new absolute total — adding 5 to a saved "26" while
  the branch holds 8 would book 31.
- ✅ **The figures are re-read when they can be.** When the connection returns, when the tab
  comes back to the foreground, on the 30-second sweep (only while the screen is known to be
  stale), and **every time the Inventory page is opened** — the page where quantities are read
  and corrected. The Inventory header states the moment the server last confirmed them.
- Verified without a database: `python _check_pos_freshness.py` (rules, and every touched
  declaration still parses) and `python _pos_freshness_browser.py` (a real browser: a saved
  copy reading 26 against a server holding 8, the refusal, and the refresh on opening the
  Inventory page).

**October 2026 — reverting a layby sale, and auditing automatic repairs**
- ✅ **Reverting a layby sale now closes the layby.** It used to return the goods but leave
  the layby sitting on the Layby tab as *active*, still offering instalments — and
  cancelling it afterwards would have put the same goods back on the shelf a **second**
  time. A reverted layby is closed with the reason recorded, its instalments stay on the
  record for a manual refund, and it leaves the default *Active laybys* view. Laybys left
  active by an earlier revert are closed the next time the tab is opened.
- ✅ An instalment can no longer be recorded against a layby whose sale was reverted, and
  such a layby can no longer be cancelled (the guard that would have double-restored its
  stock).
- ✅ **The automatic date repairs are audited.** The startup repair for project 125's
  instalment due dates, the startup `72026` → `2026` date repair, and the same repair that
  runs when the projects list is opened now record a `project_data_repaired` entry per
  value changed — naming the project, the field and the old → new date, attributed to
  **System** (nobody chose it) and filterable as *Project Data Repaired*.

**October 2026 — the till only offers what this branch actually stocks**
- ✅ **Products this branch has never stocked are hidden from the sale screen.** The
  catalogue is shared, so every item created for one shop used to fill the other shop's
  grid. The rule is taken from `product_stock`: a row for this branch means the branch
  carries the item; **no row** means it has never been here, and it is not shown. An item
  that IS carried but is out of stock today keeps its card and reads "Out of stock" — so a
  cashier can still tell a customer "we stock it, we're out".
- ✅ **The till's own counts agree with the grid.** Total Products, Low Stock and Out of
  Stock (and the lists behind them) now count what this till offers; the value and margin
  cards still total the branch's real stock. The card's sub-label reads "Stocked in this
  branch" rather than "Catalogue items".
- ✅ **One stock status decides every label.** A product now reads exactly one of **In
  stock / Low / Out of stock / Not stocked here**, from a single rule used by the till's
  product cards, the inventory table and the Inventory Excel and PDF exports — so the
  same item can never be "Low" in one place and "OK" in another. "Low" is below the
  item's **own** minimum stock level (the rule the dashboard already used) instead of a
  fixed 5 or 10, and an item this branch has never stocked reads "Not stocked here"
  rather than being dressed up as low or in stock. The Low Stock card's sub-label reads
  "Below the item's minimum". Those *"Not stocked here"* lines have since left the grid
  itself — the Inventory table and its two exports now list only what this branch carries —
  so the status survives as the rule's fallback rather than as a row operators see.
- ✅ **Nothing becomes unreachable.** The audit report and the transfer list still reach every
  product, **Add Stock** gives an item a branch row and it returns to the till, and a till
  search that finds nothing because the match belongs to the other branch says so, instead of
  inviting a duplicate product to be created. (The Inventory tab listed the whole catalogue at
  this point; it is branch-only now — see *the Inventory tab lists only what this branch
  carries*.)
- ✅ The consolidated **All Branches** view is unchanged: it is a company-wide read-only
  view, so it still lists the whole catalogue with company totals.

**October 2026 — a stock figure on screen is never trusted over the server**
- ✅ **Add Stock and Subtract now fetch the product's live figure first.** A page (or an
  offline copy) that was hours old used to offer a quantity the server then refused —
  "it says 26, but 22 cannot be removed". The box now opens on the figure the server has
  this moment, and the row, the grid and the metrics are corrected at the same time.
- ✅ **A refusal names the shop and the real number**, e.g. *"Shurugwi has 4 unit(s) of
  "Cable 2.5mm" right now, so 22 cannot be removed. The figure on your screen was out of
  date; it has been refreshed."* It also returns `available`, `total_stock` and
  `branch_name`, and the till closes the box and reloads the figures, so the same stale
  number cannot be tried twice.
- ✅ **A catalogue served from the device now says so.** When the till cannot reach the
  server it replays the catalogue it saved, and a banner states that these are the saved
  figures and the time they were saved — instead of silently showing numbers that look
  wrong against the server. Quoted sales already held for this branch are still deducted
  from the live figure, so a hold can never be spent.

**October 2026 — a session must choose its shop before it can touch stock**
- ✅ **The POS now demands the branch step.** Opening the POS on a session that has not
  chosen a branch — which is what happens when a hardware user signs in on the portal
  `/login` page instead of the Hardware POS card — shows the branch prompt (undismissable)
  and a red banner, loads **no catalogue at all**, and refuses every stock or money write
  with `needs_branch`. Choosing a branch with its access code reloads the till cleanly.
  Only `/api/login` (branch + code) and `/api/pos/switch-branch` count as choosing.
- ✅ **This closed the last cross-branch leak.** Such a session used to be *named* Shurugwi
  by the old fallback: the branch chip read "Shurugwi", every figure on screen was Shurugwi's,
  and every sale, upload, adjustment and transfer a Chegutu operator made was filed against
  Shurugwi — which is exactly why Chegutu's stock counts kept appearing in Shurugwi. Reads
  still fall back to the first branch (nothing goes invisible), but a **write** now requires
  a branch the operator has proved they can open.
- ✅ **A refused batch never costs a sale.** `/api/transactions/sync` parking the whole queue
  (no branch chosen, or the read-only view) no longer counts as an attempt against each
  queued sale, so the 25-attempt abandonment rule can no longer drop a paid sale; the batch
  is retried on the next connection, reload, manual sync or 30-second sweep. A queued layby
  refused for the same reason is held (retried), not parked as a human decision.

**October 2026 — every project field change is audited, in plain words**
- ✅ **One audit row per changed project field**, naming the field as people know it
  ("Total Bill (USD)") and showing **what it was → what it became**, who and when. This
  covers the Progress Update form, the Other Details screen (which recorded *nothing*
  before), the work-schedule save, the instalment reschedule, the instalment and deposit
  receipts, the WhatsApp receipt send, the instalment variance auto-correct, and the
  automatic completion-status recalculation.
- ✅ **Fields that were never audited** on the Progress Update form now are: project start
  date, months to pay, admin name and the work schedule.
- ✅ **The Activity Log shows the change, not the tail of a sentence** — the old value in
  red and the new value in green sit on their own line under each entry (the description
  is truncated to one line, so the values used to be invisible), with a From → To block in
  the detail modal. The User Management Audit Log reads `Total Bill (USD): 5000 → 6000`
  instead of a truncated JSON blob.
- ✅ Formatting is never treated as an edit (5,000 vs 5000, date vs timestamp), and a
  failed read of the previous values logs nothing rather than inventing a change.

**October 2026 — stock a till has promised, and layby paperwork**
- ✅ **A till no longer offers stock it has already promised.** Sales and laybys queued on
  a device hold their quantity back from that till's own figures (grid, inventory,
  low/out-of-stock and the stock checks) until the server has them, released on sync,
  discard or abandonment. Holds are kept per branch, so another shop's queued sale never
  reduces this shop's shelves, and the Add Stock box always uses the server's number so a
  hold can never be written back as real stock.
- ✅ **The layby agreement prints** from the Layby tab and from un-synced cards: shop,
  agreement number, customer name/ID/phone, the reserved goods footing to the total, the
  instalment plan with dates and states, the money position, instalments received, notes,
  terms and signature lines — including for a layby the server has not seen yet.
- ✅ The runbook's bulk-upload section was corrected: a name match in a **different
  category** is raised as a conflict row (it used to say category was never a conflict).

**October 2026 — POS stock isolation, layby, reconciliation**
- ✅ **Laybys work with no connection.** The till mints its own layby number, queues the
  layby and any instalments on the device, replays them when the connection returns, and
  parks anything the server refuses on the Layby tab with its reason (never discarding it).
- ✅ **Cancelling a layby refunds the customer.** The refund defaults to everything
  collected, can be lowered to keep a fee, is recorded as its own row, and is reported as
  money paid out in day-end.
- ✅ Cross-branch stock leaks closed: the offline catalogue cache is tagged with the branch
  that fetched it, queued offline sales record the branch they were rung in, and
  `/api/transactions/sync` refuses a sale filed against a branch other than the session.
  The bulk-upload check and the barcode lookup no longer fall back to the catalogue-wide
  total, and offline sales held for another branch are never aged out of the till's queue.
- ✅ Stock reconciliation tool at `/pos/reconciliation` (POS drawer → Stock reconciliation,
  or Inventory → Stock Reconciliation) to find and move mis-filed offline sales, with
  negative branch stock as the evidence. Audited in `stock_reconciliation_log`.
- ✅ Layby: a new payment method capturing customer name, ID number, deposit and a
  validated instalment plan, with a **Layby** sidebar tab for recording payments and
  cancelling. Takings follow the money (instalments on the day received, the sale released
  to completed on the final payment); day-end and the audit report both show layby
  separately.
- ✅ Bulk stock upload: a file that lists the same new product twice no longer creates two
  products; the rows are collapsed by name before anything is written.

**v2.0.0 - April 2026**
- ✅ Full system release
- ✅ All modules functional
- ✅ Production-ready deployment
- ✅ Comprehensive documentation

**v1.5.0 - January 2026**
- ✅ AI product classification (98% accuracy)
- ✅ WhatsApp integration
- ✅ Enhanced reporting

**v1.0.0 - October 2025**
- ✅ Initial beta release
- ✅ Core modules
- ✅ Basic functionality
