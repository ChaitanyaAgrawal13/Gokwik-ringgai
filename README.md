# Abandoned Checkout Calling System

## Setup

1. Install dependencies:
pip install -r requirements.txt

2. Add .env file

3. Run FastAPI:
uvicorn app.main:app --reload

4. Run batch manually:
python scripts/run_batch.py

## Cron (every 2 hours)
0 */2 * * * /usr/bin/python3 /path/to/scripts/run_batch.py