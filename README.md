# IdealityCLI

**A local-first CLI for discovering user pain points and market opportunities across Reddit, App Store, Trustpilot, and RemoteOK.**

Scrape. Store as JSON. Summarize with AI. Search everything. All on your machine—no database, no backend, fully offline after scraping.

---

## ✨ Features

- **🔗 4 Built-in Sources**: Reddit, Apple App Store, Trustpilot, RemoteOK
- **📊 Bulk Scraping**: Up to 2,400 Reddit posts, 500 App Store reviews, 200 Trustpilot reviews, 100+ remote jobs per query
- **🤖 AI Summaries**: Automatic Markdown reports powered by Google Gemini (free tier)
- **🔍 Full-Text Search**: Case-insensitive keyword matching across all stored data
- **💾 Local Storage**: Pure JSON files—inspect, backup, or sync however you want
- **🚀 No External Dependencies**: No database, no server, no authentication (except optional Gemini API key)
- **⚡ Interactive & CLI**: REPL mode for exploration, one-shot commands for scripting

---

## 🎯 What's It Good For?

- **Startup founders**: Find pain points in your target market (Reddit + Trustpilot)
- **Product managers**: Understand what customers love and hate about competitors (App Store reviews)
- **Job market research**: Monitor remote job demand (RemoteOK)
- **Sales/GTM**: Validate market size and messaging before building
- **Content creators**: Discover trending topics and user frustrations

---

## 🛠️ Requirements

- **Python 3.10+**
- **Google Gemini API key** (free tier; only needed for `summarize` command)
  - Get one free at [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
  - No credit card required
  - No summarization limits in free tier

---

## ⚡ Quick Start

### 1. Clone & install

```bash
git clone https://github.com/<your-username>/IdealityCLI.git
cd IdealityCLI
pip install -r requirements.txt
```

### 2. Set up Gemini API key (optional, only for summarization)

```bash
cp .env.example .env
# Open .env and paste your free Gemini API key
# GEMINI_API_KEY=your_key_here
```

### 3. Try it out

```bash
# Interactive REPL mode
python main.py
# or if you installed globally:
ideality

# One-shot commands (no REPL)
python main.py store reddit "saas pain points"
python main.py search "expensive"
```

---

## 📖 Installation

### Installation with global command (recommended)

```bash
pip install -e .
```

Then you can run `ideality` from anywhere:

```bash
ideality store reddit python
ideality summarize reddit python
```

### Installation without global command

```bash
pip install -r requirements.txt
python main.py
```

### Verify installation

```bash
python main.py --help
```

Should show:

```
usage: main.py {scrape,store,summarize,search} ...

positional arguments:
  {scrape,store,summarize,search}
    scrape      Scrape a source (prints to stdout, does not save)
    store       Scrape a source and save to /data/<source>/<id>.json
    summarize   Summarize a stored JSON file using Gemini
    search      Search across all stored JSON files
```

### Set up your Gemini API key

**Only required for the `summarize` command.** Scraping works without it.

1. Get a free key: [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Create `.env` in the project root:

```bash
cp .env.example .env
```

3. Open `.env` and paste your key:

```
GEMINI_API_KEY=your_actual_key_here
```

**Why Gemini?** It's free, has a huge context window (~1M tokens), and works great for synthesizing large datasets (500+ items in one call).

---

## 🎮 Usage

### Launch the interactive shell

```bash
ideality
```

This opens an interactive REPL:

```
╔══════════════════════════════════════════╗
║           IdealityCLI v1.0.0             ║
║  Local scraper · storage · summarizer    ║
╚══════════════════════════════════════════╝

ideality>
```

Type `help` for command details, or just start scraping:

```bash
ideality> store reddit "project management"
ideality> summarize reddit project_management
ideality> search "collaboration"
```

**Or use one-shot mode** (useful for scripts, cron jobs, CI):

```bash
ideality scrape reddit python
ideality store trustpilot notion
ideality summarize appstore 6480417616
ideality search "too expensive"
```

---

## 📚 Commands

### `scrape` — Fetch from a source (stdout only, no storage)

Prints results to terminal without saving. Useful for preview, debugging, or piping to other tools.

```bash
ideality> scrape reddit python
ideality> scrape reddit "project management"
ideality> scrape trustpilot notion
ideality> scrape appstore 6480417616
ideality> scrape remoteok "machine learning"
```

**Reddit behavior:**
- Single word → scrapes that subreddit (4 sort passes: hot, top/all, top/year, new)
- Multi-word phrase → Reddit site-wide search across 4 sort orders + auto-discovers up to 5 related subs + deduplicates by post URL

**App Store:** Use the numeric app ID from the URL (`apps.apple.com/us/app/id<ID>`) or an app name:

```bash
ideality> scrape appstore 6480417616       # By ID
ideality> scrape appstore "figma"          # By name — auto-resolves to ID
```

**Trustpilot:** Pass the company name:

```bash
ideality> scrape trustpilot "notion"
ideality> scrape trustpilot "asana"
```

The scraper auto-discovers the latest company page slug.

**RemoteOK:** Pass a job role, tech stack, or skill:

```bash
ideality> scrape remoteok "python developer"
ideality> scrape remoteok "data scientist"
ideality> scrape remoteok "ai engineer"
```

Multi-word queries are automatically split and queried separately.

---

### `store` — Scrape and save to JSON

Scrapes a source and saves results to `/data/<source>/<query>.json` with auto-mkdir. Re-running the same query overwrites the file.

```bash
ideality> store reddit python
# → data/reddit/python.json

ideality> store reddit "saas pain points"
# → data/reddit/saas_pain_points.json

ideality> store trustpilot notion
# → data/trustpilot/notion.json

ideality> store appstore 6480417616
# → data/appstore/6480417616.json

ideality> store remoteok "product manager"
# → data/remoteok/product_manager.json
```

**Pro tip:** Store multiple related queries, then search across them:

```bash
ideality> store reddit "project management"
ideality> store trustpilot asana
ideality> store trustpilot notion
ideality> search "collaboration"  # Searches all three files
```

---

### `summarize` — AI-powered Markdown report

Reads a stored JSON file, sends it to **Google Gemini**, and generates a structured Markdown report.

```bash
ideality> summarize appstore 6480417616
# Reads:  data/appstore/6480417616.json
# Writes: summaries/appstore_6480417616.md
```

**Report includes:**
1. Executive summary (overview)
2. Top recurring themes
3. Pain points (customer frustrations)
4. Positive signals (what users love)
5. Opportunities (unsolved problems, feature gaps)
6. Notable quotes (representative user feedback)
7. Metadata (total items processed, averages, sources)

**Performance:**
- ~500 items (800k chars) = 1 LLM call = 30–90 seconds
- Larger datasets = auto-split into chunks, each summarized separately, then merged
- Free tier is fast enough for typical use

**Requires:** `GEMINI_API_KEY` in `.env`

---

### `search` — Keyword search across all data

Case-insensitive search across all JSON files in `/data`. Great for finding patterns across multiple sources.

```bash
ideality> search "expensive"
ideality> search "onboarding"
ideality> search "customer support"
ideality> search "ui ux"
```

Results show:
- Matched text snippet
- Source file path
- Item ID (to trace back to the original record)

**Example output:**

```
[data/trustpilot/notion.json] "The pricing is way too expensive for small teams"
[data/reddit/saas_pain_points.json] "Notion is expensive, Airtable is cheaper"
[data/appstore/6480417616.json] "Great product but pricing makes it hard to justify"
```

---

## 📊 Data Sources Explained

### Reddit

**What:** Posts from subreddits and site-wide search results

**How it works:**
- Single-word queries (e.g., `python`) → scrapes that subreddit across 4 sort orders (hot, top/all, top/year, new)
- Multi-word/phrase queries (e.g., `saas pain points`) → Reddit site-wide search + discovers up to 5 related subreddits + scrapes each one
- Auto-deduplicates by post URL

**Volume:** Up to ~2,400 unique posts per query

**Quality:** Raw, honest user feedback. Lots of noise; good for breadth.

**Rate limiting:** 1.5s delay between requests (respectful)

**No auth needed:** Uses Reddit's public JSON API

**Best for:** Finding problems, emotional language, what's trending

**Limitations:**
- Reddit's search is fuzzy and imperfect
- Upvote bias (popular opinions over niche pain points)
- Bot/spam posts included

---

### App Store

**What:** Apple App Store reviews for any app

**How it works:**
- Pass an app name or ID (from the URL)
- Scraper auto-resolves names to app IDs via iTunes API
- Fetches reviews from Apple's official RSS feed

**Volume:** Up to 500 reviews (10 pages × 50 per page)

**Quality:** Structured, timestamped, includes ratings (1–5 stars)

**Rate limiting:** Minimal; Apple doesn't throttle RSS

**No auth needed:** Uses Apple's official iTunes RSS JSON API (public, no key required)

**Best for:** Quantified feedback (star ratings), direct from paying customers

**Limitations:**
- Only covers iOS/macOS apps (not Android, web, etc.)
- Reviews often generic ("great app!"); less detail than Trustpilot
- Older reviews may not be available (depends on app popularity)

---

### Trustpilot

**What:** Business/SaaS reviews and ratings from Trustpilot

**How it works:**
- Pass a company name (e.g., `notion`, `asana`)
- Scraper searches Trustpilot, finds the company page, extracts reviews
- Auto-handles pagination

**Volume:** Up to 200 reviews (10 pages × 20 per page)

**Quality:** Detailed, often lengthy reviews. Verified reviewers preferred.

**Rate limiting:** 1.0s delay between requests

**No auth needed:** HTML scraping of public pages

**Best for:** Deep customer feedback, direct comparison shopping, feature complaints

**Limitations:**
- Company slug must be exact or close (e.g., "notion" works; "notion app" might not)
- If the company doesn't have a Trustpilot page, returns 0 results
- HTML layout changes can break selectors (rare but possible)

---

### RemoteOK

**What:** Remote job listings from RemoteOK

**How it works:**
- Pass a job role or tech skill (e.g., `data scientist`, `python developer`)
- Multi-word queries are split into individual tags and queried separately
- Results are merged and deduplicated by job ID
- Job descriptions are auto-cleaned of HTML

**Volume:** ~50–200 jobs per query (depending on term popularity)

**Quality:** Structured job data (title, company, link, salary/contract info)

**Rate limiting:** None observed; API is generous

**No auth needed:** RemoteOK's free public JSON API

**Best for:** Job market demand, salary expectations, tech stack trends

**How multi-word queries work:**

| Input | Splits to | Queries |
|---|---|---|
| `python developer` | `["python", "developer"]` | `tag=python` + `tag=developer` |
| `data scientist` | `["data", "scientist"]` | `tag=data` + `tag=scientist` |
| `ai engineer` | `["ai", "engineer"]` | `tag=ai` + `tag=engineer` |

(The API only accepts single-word tags, so multi-word inputs are split automatically.)

**Limitations:**
- Only returns jobs available on RemoteOK (doesn't aggregate from other job boards)
- Remote-only (no office jobs)
- Salary info is optional (many jobs don't include it)

---

## 🧠 Typical Workflows

### Workflow 1: Validate a market before building a startup

```bash
ideality> store reddit "project management"
ideality> store trustpilot asana
ideality> store trustpilot notion
ideality> store appstore 6480417616  # Asana app ID
ideality> search "expensive"
ideality> search "too complicated"
ideality> summarize reddit project_management
```

**Output:** Markdown report with themes, pain points, opportunities across 4 sources.

### Workflow 2: Competitor analysis

```bash
ideality> store appstore 6480417616  # Competitor's app
ideality> store trustpilot "competitor"
ideality> summarize appstore 6480417616
ideality> search "missing feature"
```

**Output:** What users complain about = opportunities for your product.

### Workflow 3: Job market research

```bash
ideality> store remoteok "machine learning"
ideality> store remoteok "data engineer"
ideality> store remoteok "ai engineer"
ideality> search "python"
ideality> search "salary"
ideality> summarize remoteok machine_learning
```

**Output:** Job trends, required skills, salary expectations.

### Workflow 4: Content inspiration

```bash
ideality> store reddit "saas bloat"
ideality> store reddit "minimalist tools"
ideality> search "feature bloat"
ideality> search "simplicity"
```

**Output:** Top pain points = article topics.

---

## 🗂️ Project Structure

```
IdealityCLI/
│
├── main.py                          # CLI entrypoint (REPL + one-shot)
├── requirements.txt                 # Python dependencies
├── setup.py                         # Package config (for `pip install -e .`)
├── README.md                        # This file
├── .env.example                     # Template for API keys
├── .gitignore                       # Git ignore (data/, summaries/, .env)
│
├── src/
│   ├── __init__.py
│   │
│   ├── cli/                         # Command handlers
│   │   ├── __init__.py
│   │   ├── scrape.py                # `scrape` command
│   │   ├── store.py                 # `store` command
│   │   ├── summarize.py             # `summarize` command
│   │   └── search.py                # `search` command
│   │
│   ├── scrapers/                    # Data source modules
│   │   ├── __init__.py
│   │   ├── reddit.py                # Reddit API scraper (multi-pass)
│   │   ├── appstore.py              # Apple iTunes RSS API scraper
│   │   ├── trustpilot.py            # Trustpilot HTML scraper
│   │   └── remoteok.py              # RemoteOK JSON API scraper
│   │
│   ├── summarize/
│   │   ├── __init__.py
│   │   └── summarizer.py            # Gemini API integration + chunking
│   │
│   └── utils/
│       ├── __init__.py
│       ├── fileio.py                # JSON I/O with auto-mkdir
│       ├── text.py                  # Text cleaning + keyword search
│       └── chunk.py                 # LLM context window chunking
│
├── data/                            # Stored scraped data (git-ignored)
│   ├── reddit/
│   ├── appstore/
│   ├── trustpilot/
│   └── remoteok/
│
└── summaries/                       # Generated Markdown reports (git-ignored)
```

---

## ⚙️ Configuration

### Environment variables (`.env`)

```
GEMINI_API_KEY=your_free_gemini_api_key_here
```

**Only required for `summarize`.** All scraping commands work without it.

### Tuning scrapers

All scraper limits are configurable. Edit these constants in the scraper files:

| File | Setting | Default | Purpose |
|---|---|---|---|
| `src/scrapers/reddit.py` | `MAX_POSTS_PER_SORT` | `100` | Posts per sort pass (hot, top, etc.) |
| `src/scrapers/reddit.py` | `MAX_SUBREDDITS` | `5` | Related subreddits to discover |
| `src/scrapers/reddit.py` | `CRAWL_DELAY` | `1.5` | Seconds between Reddit API calls |
| `src/scrapers/appstore.py` | `MAX_PAGES` | `10` | Pages of reviews (50/page = 500 max) |
| `src/scrapers/appstore.py` | `CRAWL_DELAY` | `0.5` | Seconds between Apple API calls |
| `src/scrapers/trustpilot.py` | `MAX_PAGES` | `10` | Pages of reviews (20/page = 200 max) |
| `src/scrapers/trustpilot.py` | `CRAWL_DELAY` | `1.0` | Seconds between Trustpilot requests |
| `src/summarize/summarizer.py` | `CHUNK_MAX_CHARS` | `800000` | Max chars per LLM call (larger = fewer API calls) |
| `src/summarize/summarizer.py` | `GEMINI_MODEL` | `gemini-2.5-flash` | Model to use |

---

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'google.generativeai'"

Install dependencies:

```bash
pip install -r requirements.txt
```

### "GEMINI_API_KEY not found" when running `summarize`

1. Verify `.env` exists in project root
2. Verify it contains your actual key: `GEMINI_API_KEY=sk_...`
3. Restart your Python shell or IDE

```bash
cat .env  # Verify the key is there
```

### "0 results" for a scrape

Possible causes:

- **Reddit:** Subreddit doesn't exist or no posts match your query
- **App Store:** App ID is incorrect or app doesn't exist
- **Trustpilot:** Company doesn't have a Trustpilot page (search their domain on trustpilot.com)
- **RemoteOK:** Job tag doesn't exist (try lowercase; check RemoteOK's job listings for available tags)

**How to debug:**
1. Try a simpler query (e.g., `scrape reddit python`)
2. Check the source website directly to confirm data exists
3. Try a different term

### Scraper is slow or hitting rate limits

All scrapers have built-in delays (Reddit: 1.5s, Trustpilot: 1.0s, others minimal). These are intentional and respectful.

If you need faster scraping:
1. Reduce `CRAWL_DELAY` in the scraper file (not recommended; can get you blocked)
2. Use smaller `MAX_PAGES` / `MAX_SUBREDDITS` values
3. Run parallel instances for different queries

### Summarize is very slow or timing out

This usually means:
- **Large dataset** (500+ items, 800k+ characters)
- **First-time Gemini API setup** (API provisioning delay)

**Solutions:**
- Just wait; summarizing 500 items typically takes 30–90 seconds
- Reduce the dataset size (fewer `MAX_PAGES` in scraper)
- Switch from `gemini-2.5-flash` to a faster model (not recommended; flash is already optimized)

### "Trustpilot returned 0 results"

The company may not have a Trustpilot page, or the name might be slightly different.

**Debug steps:**
1. Search Trustpilot directly: https://www.trustpilot.com/
2. Find the exact company name or domain
3. Try again with the exact spelling

Example:

```bash
ideality> scrape trustpilot "monday.com"  # Not "monday"
```

---

## 📈 Use Cases & Examples

### SaaS market research

Find pain points in competing products:

```bash
ideality> store appstore 6480417616  # Figma app (hypothetical ID)
ideality> store trustpilot figma
ideality> store reddit "design tools"
ideality> summarize appstore 6480417616
```

Output = competitive analysis document.

### Job market analysis

Track demand for specific skills:

```bash
ideality> store remoteok "rust"
ideality> store remoteok "go"
ideality> store remoteok "python"
ideality> search "salary"
ideality> search "senior"
```

Output = job market trends by skill.

### Red-teaming your product

Find complaints about similar products:

```bash
ideality> store trustpilot "zendesk"
ideality> store trustpilot "intercom"
ideality> search "slow"
ideality> search "expensive"
ideality> search "api"
```

Output = feature gaps to address.

---

## 🔐 Privacy & Security

- **All data is stored locally** in `/data/` on your machine (not cloud-synced)
- **API keys are never logged** (only passed securely to Google/APIs)
- **.env files are git-ignored** by default; never commit your API key
- **No telemetry** or analytics; your queries are private
- **Public APIs only:** No scraping of private user accounts or protected content

---

## 📝 Notes & Limitations

### General

- **No database:** Everything is plain JSON files. This is intentional (simplicity, portability, transparency).
- **No sync:** Store your `/data/` directory in cloud storage (Dropbox, iCloud, etc.) if you want sync.
- **Large datasets:** Searching 1000s of files can be slow; consider organizing by date or source.

### Reddit

- Rate-limited to 100 results per API call; the scraper makes multiple calls for breadth
- Search algorithm is fuzzy; exact phrase matching not always available
- Archived posts (6+ months old) are not indexable by Reddit's API

### App Store

- Only covers iOS/macOS (not Android)
- Older apps may have limited review history
- Reviews are sorted by helpfulness, not recency

### Trustpilot

- Company must have a verified Trustpilot page
- HTML layout changes can break selectors (rare; auto-fixable)

### RemoteOK

- Remote jobs only (no office positions)
- Only jobs listed on RemoteOK; doesn't aggregate from other boards
- API only accepts single-word tags; multi-word queries are split automatically

---

## 🤝 Contributing

Ideas for improvements?

- Add a new scraper (Twitter, G2, ProductHunt, Stack Overflow, etc.)
- Improve existing scrapers (better parsing, faster crawling, etc.)
- New search features (date filters, source filters, regex)
- Visualization tools (charts, word clouds from summaries)

**Before submitting a PR:**

1. Test your changes: `python main.py <command>`
2. Verify no API keys leak in code
3. Update README if adding new features
4. Run `pip install -e .` locally to test global install

---

## 📄 License

MIT

---

## 🙋 Questions?

Open an issue on GitHub or just run:

```bash
ideality --help
```

