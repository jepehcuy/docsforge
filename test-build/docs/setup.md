# Setup & Deployment

## Prerequisites

- **Runtime**: Python 3.8+
- **Package Manager**: pip
- **Database**: SQLite (included with Python)

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd promptforge
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` with your actual configuration values.

## Environment Variables

| Variable | Description | Required | Default/Example |
|----------|-------------|----------|-----------------|
| `OPENAI_API_KEY` | OpenAI API authentication key | Yes | `your-api-key-here` |
| `OPENAI_BASE_URL` | OpenAI API endpoint URL | No | `https://api.openai.com/v1` |
| `MIMO_MODEL` | Model identifier for MIMO service | Yes | `xiaomi/mimo-v2.5-pro` |
| `DATABASE_URL` | SQLite database file path | No | `sqlite:///data/promptforge.db` |

## Local Development

1. **Ensure environment is activated**
   ```bash
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Start the development server**
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```
   
   The application will be available at `http://localhost:8000`

3. **Access API documentation**
   - Swagger UI: `http://localhost:8000/docs`
   - ReDoc: `http://localhost:8000/redoc`

4. **Database initialization**
   The SQLite database will be created automatically at the path specified in `DATABASE_URL` on first run. Ensure the `data/` directory exists:
   ```bash
   mkdir -p data
   ```

## Production Deployment

**TODO**: No Dockerfile or Procfile found in the provided configuration files. 

For production deployment, consider:

- Using a production ASGI server (uvicorn with workers or gunicorn with uvicorn workers)
- Setting up proper environment variable management (secrets manager, encrypted configs)
- Configuring a reverse proxy (nginx, Caddy)
- Implementing database backups for the SQLite file
- Using a process manager (systemd, supervisor) or container orchestration

**Example production command**:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4