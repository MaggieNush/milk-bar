# Mama's Milk Bar Management System

A simple system for a Kenyan milk bar to manage products, clients, suppliers, deliveries, and daily sales. It includes:

- CLI app: `milk_bar.py`
- Streamlit dashboard: `milk_dashboard.py`
- Local JSON storage: `milk_bar_data.json` (ignored by git)
- Seeder script: `seed_data.py` to generate sample products, clients, suppliers, and deliveries

## Features
- Product inventory with units, prices, and automatic stock updates
- Client management and per-client sales history
- Supplier management and recording deliveries
- Sales recording with itemized products per sale
- Dashboard with KPIs, recent sales/deliveries, filters, and management pages

## Getting Started

### 1) Install dependencies
```bash
pip install -r requirements.txt
```

### 2) Seed sample data (optional)
```bash
python seed_data.py
```

### 3) Run the CLI app
```bash
python milk_bar.py
```

### 4) Run the Streamlit dashboard
```bash
streamlit run milk_dashboard.py
```
Then open http://localhost:8501

## Deploy to Streamlit Community Cloud
1. Push this repository to GitHub (see below).
2. Go to https://share.streamlit.io/ and sign in with GitHub.
3. Click "New app" and select your repo and branch.
4. Set the entry point to `milk_dashboard.py`.
5. Add environment settings if needed (none required by default).
6. Deploy. Streamlit Cloud will install packages from `requirements.txt` automatically.

Note: `milk_bar_data.json` is gitignored to avoid committing local data. In Streamlit Cloud, the app starts with empty data unless you programmatically seed it or remove the file from `.gitignore` (not recommended for real data). You can include a seeding button in the app if desired.

## Project Structure
```
.
├── milk_bar.py            # CLI app
├── milk_dashboard.py      # Streamlit UI
├── seed_data.py           # Seeds sample data
├── milk_bar_data.json     # Local JSON storage (ignored by git)
├── requirements.txt       # Python dependencies
├── .gitignore             # Ignore venv, data files, caches
└── README.md
```

## Notes
- For best results, run in a virtual environment.
- Prices and currency are in Kenyan Shillings (Ksh).
- Data is stored locally in a JSON file for simplicity.
