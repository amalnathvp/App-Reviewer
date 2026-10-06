# App Reviewer

**App Reviewer** is an automated Product Management Intelligence platform that ingests customer reviews from both **Google Play Store** and **Apple App Store**, processes them through a 14-step analytical framework, and produces actionable PM insights—complete with sentiment graphs, version regression alerts, churn warnings, and visual heatmaps.

---

## Deploy to Vercel

This repository is pre-configured and 100% Vercel-ready.

### Option 1: Deploy with Vercel CLI (Recommended)

1. **Install Vercel CLI** (if not already installed):
   ```bash
   npm i -g vercel
   ```

2. **Deploy to Preview**:
   ```bash
   vercel
   ```
   Follow the prompts in the terminal:
   - *Set up and deploy?* **Y**
   - *Which scope?* Select your account
   - *Link to existing project?* **N**
   - *Project name?* `app-reviewer`
   - *In which directory is your code located?* `./`
   - Vercel will detect `api/index.py` and `vercel.json` automatically.

3. **Deploy to Production**:
   ```bash
   vercel --prod
   ```

---

### Option 2: Deploy via GitHub + Vercel Dashboard

1. **Push this repository to GitHub**:
   ```bash
   git add .
   git commit -m "Configure Vercel deployment"
   git push origin main
   ```

2. **Import into Vercel**:
   - Go to [vercel.com/new](https://vercel.com/new).
   - Select your GitHub repository (`App-Reviewer`).
   - Leave Framework Preset as **Other** (detected automatically via `vercel.json`).
   - Click **Deploy**.

Vercel will install dependencies from `requirements.txt`, bundle `api/index.py`, deploy the serverless functions, and serve all static frontend files globally from Vercel's Edge CDN.

---

## Project Structure

```text
Product/
├── api/
│   └── index.py            # Vercel Serverless Function entry point (ASGI)
├── app/
│   ├── collector.py        # Dual-store review scraper (Play Store + App Store)
│   └── pm_agent.py         # 14-step PM Intelligence analysis engine
├── frontend/               # Frontend source files (HTML, CSS, JS)
│   ├── css/style.css       # Clean white & blue design system
│   ├── js/app.js           # Visual dashboard logic & Chart.js rendering
│   └── index.html          # Clean single-input UI
├── public/                 # Edge CDN-optimized static assets for Vercel
│   ├── index.html
│   └── static/
├── main.py                 # FastAPI application & local development server
├── vercel.json             # Vercel serverless functions & rewrite rules
├── requirements.txt        # Python dependencies for Vercel runtime
└── .vercelignore           # Excluded files for lightweight deployments
```

---

## Local Development

To run the application locally:

```bash
# Install dependencies
pip install -r requirements.txt

# Start local server
uvicorn main:app --reload --port 8000
```

Open your browser at `http://127.0.0.1:8000`.

---

## Key Features

- **Dual-Store Auto-Collection**: Ingests reviews concurrently from both Google Play Store and Apple App Store by entering an app name or URL.
- **Version Attribution & Regression Alerts**: Pinpoints bugs and satisfaction drops across specific app versions (`v10.54 (Android)` vs. `v10.55 (iOS)`).
- **Churn & Cohort Analysis**: Identifies competitor migration threats and user retention hazards.
- **Visual Analytics**: Interactive timeline sentiment charts, rating breakdown charts, problem priority bars, and an interactive category-vs-severity heatmap.
- **Clean White & Blue UI**: Modern, accessible interface designed for product leaders.
