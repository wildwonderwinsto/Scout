# YouTube Trend Scout

A tool to discover trending YouTube videos and channels using data-driven ranking (Breakout Score, VPH velocity, outlier detection) rather than gut feel.

## Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
# Edit .env and add your YouTube Data API v3 key
```

## Run

```bash
uvicorn app.main:app --reload
```

API docs available at `http://localhost:8000/docs`

## Test

```bash
pytest
```

## Architecture

- **FastAPI** REST API backend
- **SQLAlchemy** ORM with SQLite (swappable to PostgreSQL)
- **google-api-python-client** for YouTube Data API v3
- **Pydantic v2** for validation and serialization

## Project Structure

```
app/
├── main.py               # FastAPI app entry point
├── config.py             # Environment settings via pydantic-settings
├── database.py           # SQLAlchemy engine + session
├── models/               # SQLAlchemy ORM models
│   ├── channel.py
│   ├── video.py
│   └── snapshot.py       # Historical view snapshots for VPH
├── schemas/              # Pydantic response/request models
│   ├── channel.py
│   ├── video.py
│   └── common.py
├── services/             # Business logic
│   ├── youtube_client.py # YouTube API wrapper
│   ├── data_fetcher.py   # Fetch + store orchestration
│   └── calculations.py   # Breakout score, VPH (future)
├── routers/              # API endpoints
│   ├── health.py
│   ├── channels.py
│   └── videos.py
└── utils/
    └── logger.py
```
