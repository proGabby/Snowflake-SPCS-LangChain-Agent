# Snowflake SPCS LangChain Agent

A containerized LangChain agent for Snowflake SPCS with vLLM integration, featuring comprehensive monitoring and security controls.

## Quick Start

### 1. Environment Setup

```bash
# Copy the example environment file
cp example.env .env

# Edit .env with your actual Snowflake credentials
nano .env
```

### 2. Install Dependencies

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r utils/requirements.txt
```

### 3. Run the Application
# Lightweight setup (app + mock vLLM)
docker compose -f docker/docker-compose.lightweight.yml up --build -d

# Full monitoring stack
docker compose -f docker/docker-compose.monitoring.yml up --build -d
```

## Monitoring

- **Application**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Metrics**: http://localhost:8001/metrics
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SNOWFLAKE_ACCOUNT` | Snowflake account identifier | Required |
| `SNOWFLAKE_USER` | Snowflake username | Required |
| `SNOWFLAKE_PASSWORD` | Snowflake password | Required |
| `SNOWFLAKE_WAREHOUSE` | Snowflake warehouse | Required |
| `SNOWFLAKE_DATABASE` | Snowflake database | Required |
| `VLLM_BASE_URL` | vLLM service endpoint | http://localhost:8001 |
| `VLLM_MODEL_NAME` | LLM model name | microsoft/DialoGPT-small |
| `SECRET_KEY` | JWT secret key | Change in production! |
| `GRAFANA_ENABLED` | Enable Grafana integration | true |

### Security Settings

- **Read-only access**: Configured to prevent DROP/DELETE/UPDATE operations
- **Rate limiting**: 100 requests per hour by default
- **Table restrictions**: Limit access to specific tables via `SNOWFLAKE_ALLOWED_TABLES`
- **Row limits**: Maximum 10,000 rows per query (configurable)

## Project Structure

```
├── app/                    # Main application code
│   ├── agent/             # LangChain agent implementation
│   ├── auth/              # Authentication & security
│   ├── config/            # Configuration management
│   ├── integrations/      # External service integrations
│   └── models/            # Pydantic models
├── docker/                # Docker configurations
├── monitoring/            # Prometheus & Grafana configs
├── utils/                 # Utility scripts and requirements
├── example.env            # Environment template
├── .gitignore            # Git ignore rules
└── README.md             # This file
```

## Security

- Environment files with secrets are ignored by Git
- JWT-based authentication with configurable expiration
- CORS protection for web clients
- Rate limiting to prevent abuse
- SQL injection protection through parameterized queries

## API Endpoints

- `GET /` - Application status
- `GET /health` - Health check
- `POST /query` - Process natural language queries
- `GET /tables` - List available tables
- `GET /tables/{table}/schema` - Get table schema
- `GET /status` - Agent configuration status

## Development

### Adding New Features

1. Update models in `app/models/schemas.py`
2. Add endpoints in `app/main.py`
3. Implement business logic in `app/agent/` or `app/integrations/`
4. Add tests and update documentation

### Monitoring

The application includes comprehensive monitoring with:
- Prometheus metrics collection
- Grafana dashboards
- Health checks
- Performance tracking
- Error monitoring

