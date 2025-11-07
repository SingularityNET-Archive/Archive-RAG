# Web Hosting Guide for Archive-RAG

This guide explains how to host your Archive-RAG system publicly using the built-in web interface.

## Quick Start

### 1. Create an Index

First, ensure you have an index file. If you don't have one yet:

```bash
# Index sample data from GitHub
archive-rag index "https://raw.githubusercontent.com/SingularityNET-Archive/SingularityNET-Archive/refs/heads/main/Data/Snet-Ambassador-Program/Meeting-Summaries/2025/meeting-summaries-array.json" indexes/sample-meetings.faiss --no-redact-pii
```

### 2. Start the Web Server

```bash
# Start on default port 8000
archive-rag web

# Or specify custom host and port
archive-rag web --host 0.0.0.0 --port 8080

# For development with auto-reload
archive-rag web --reload
```

### 3. Access the Interface

Open your browser and navigate to:
- **Local access**: http://localhost:8000
- **Network access**: http://YOUR_IP:8000

## Configuration

### Environment Variables

You can configure the web server using environment variables:

```bash
# Set default index file path
export ARCHIVE_RAG_INDEX_PATH="indexes/sample-meetings.faiss"

# Start the server
archive-rag web
```

### Default Index Selection

If `ARCHIVE_RAG_INDEX_PATH` is not set, the server will:
1. Look for `indexes/sample-meetings.faiss`
2. If not found, use the first `.faiss` file found in `indexes/`
3. If no index is found, return an error

## API Endpoints

The web server provides both a web interface and a REST API:

### Web Interface
- `GET /` - Web UI for querying

### REST API
- `POST /api/query` - Query the RAG system
- `GET /api/health` - Health check endpoint

### Example API Usage

```bash
# Query via API
curl -X POST "http://localhost:8000/api/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What decisions were made about budget allocation?",
    "top_k": 5
  }'

# Health check
curl http://localhost:8000/api/health
```

## Deployment Options

### Option 1: Railway

1. **Create a Railway account** at https://railway.app

2. **Create a new project** and connect your GitHub repository

3. **Add environment variables**:
   - `ARCHIVE_RAG_INDEX_PATH`: Path to your index file (if not using default)

4. **Configure the start command**:
   ```bash
   archive-rag web --host 0.0.0.0 --port $PORT
   ```

5. **Deploy**: Railway will automatically deploy when you push to your repository

### Option 2: Render

1. **Create a Render account** at https://render.com

2. **Create a new Web Service**:
   - Connect your GitHub repository
   - Build command: `pip install -r requirements.txt`
   - Start command: `archive-rag web --host 0.0.0.0 --port $PORT`

3. **Add environment variables**:
   - `ARCHIVE_RAG_INDEX_PATH`: Path to your index file

4. **Deploy**: Render will build and deploy your service

### Option 3: Fly.io

1. **Install Fly CLI**: `curl -L https://fly.io/install.sh | sh`

2. **Create a `fly.toml`**:
   ```toml
   app = "your-app-name"
   primary_region = "iad"

   [build]

   [http_service]
     internal_port = 8000
     force_https = true
     auto_stop_machines = true
     auto_start_machines = true
     min_machines_running = 0

   [[services]]
     protocol = "tcp"
     internal_port = 8000
   ```

3. **Deploy**:
   ```bash
   fly launch
   fly deploy
   ```

### Option 4: Docker

1. **Create a `Dockerfile`**:
   ```dockerfile
   FROM python:3.11-slim

   WORKDIR /app

   # Install system dependencies
   RUN apt-get update && apt-get install -y \
       build-essential \
       && rm -rf /var/lib/apt/lists/*

   # Copy requirements and install Python dependencies
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt

   # Download spaCy model
   RUN python -m spacy download en_core_web_sm

   # Copy application code
   COPY . .

   # Install the package
   RUN pip install -e .

   # Expose port
   EXPOSE 8000

   # Start the web server
   CMD ["archive-rag", "web", "--host", "0.0.0.0", "--port", "8000"]
   ```

2. **Build and run**:
   ```bash
   docker build -t archive-rag .
   docker run -p 8000:8000 -e ARCHIVE_RAG_INDEX_PATH=indexes/sample-meetings.faiss archive-rag
   ```

### Option 5: VPS (DigitalOcean, AWS EC2, etc.)

1. **Set up your server** with Python 3.11+

2. **Clone and install**:
   ```bash
   git clone <your-repo>
   cd Archive-RAG
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   pip install -e .
   ```

3. **Create a systemd service** (`/etc/systemd/system/archive-rag.service`):
   ```ini
   [Unit]
   Description=Archive-RAG Web Server
   After=network.target

   [Service]
   Type=simple
   User=your-user
   WorkingDirectory=/path/to/Archive-RAG
   Environment="PATH=/path/to/Archive-RAG/venv/bin"
   Environment="ARCHIVE_RAG_INDEX_PATH=indexes/sample-meetings.faiss"
   ExecStart=/path/to/Archive-RAG/venv/bin/archive-rag web --host 0.0.0.0 --port 8000
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

4. **Start the service**:
   ```bash
   sudo systemctl enable archive-rag
   sudo systemctl start archive-rag
   ```

5. **Set up Nginx reverse proxy** (optional but recommended):
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;

       location / {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

## Security Considerations

### For Production Deployment

1. **Restrict CORS**: Update `src/web/app.py` to restrict CORS origins:
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["https://your-domain.com"],  # Replace with your domain
       allow_credentials=True,
       allow_methods=["GET", "POST"],
       allow_headers=["*"],
   )
   ```

2. **Add Rate Limiting**: Consider adding rate limiting middleware to prevent abuse

3. **Use HTTPS**: Always use HTTPS in production (most platforms provide this automatically)

4. **Environment Variables**: Store sensitive configuration in environment variables, not in code

5. **Authentication**: For private deployments, consider adding authentication middleware

## Troubleshooting

### Index Not Found

If you see "No index file found":
1. Ensure you've created an index using `archive-rag index`
2. Set `ARCHIVE_RAG_INDEX_PATH` environment variable
3. Check that the index file exists in the `indexes/` directory

### Port Already in Use

If port 8000 is already in use:
```bash
# Use a different port
archive-rag web --port 8080
```

### Memory Issues

The RAG system loads models into memory. For large deployments:
- Ensure your server has at least 4GB RAM
- Consider using a larger instance for production
- Monitor memory usage and scale as needed

## Performance Tips

1. **Pre-load models**: The first query may be slower as models load
2. **Use caching**: Consider adding Redis for query result caching
3. **Load balancing**: For high traffic, use multiple instances behind a load balancer
4. **CDN**: Serve static assets through a CDN if customizing the UI

## Next Steps

- Customize the web interface in `src/web/app.py`
- Add authentication if needed
- Set up monitoring and logging
- Configure backups for your index files


