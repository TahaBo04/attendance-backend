# Attendance Backend

FastAPI service for camera-based attendance (face recognition).

## Deploy (Render)

1. Create a Postgres (Render Managed) or get a free Neon/Supabase DB.
2. Fork/clone this repo, connect to Render **Web Service** using this repo.
3. Render reads `render.yaml` and builds the Docker image.
4. Set environment variables:
   - `DATABASE_URL`: e.g. postgres://...
   - `SECRET_TOKEN`: any long random string
   - `ALLOWED_ORIGINS`: your GitHub Pages origin (comma-separated if many)

## Local Dev
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=postgres://...  # or use a local Postgres
uvicorn app:app --reload
