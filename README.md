# Snowflake SPCS LangChain Agent

A containerized LangChain agent for Snowflake SPCS with Gemini AI integration, featuring comprehensive monitoring and security controls.

## Quick Start

### 1. Environment Setup

```bash
# Copy the example environment file
cp example.env .env

# Edit .env with your actual Snowflake credentials and Google API key
nano .env
```

### 2. Install Dependencies

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Run the Application

```bash
# Lightweight setup (app + Gemini AI)
docker compose -f docker/docker-compose.lightweight.yml up --build -d
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
| `SNOWFLAKE_ROLE` | Snowflake role | PUBLIC |
| `GOOGLE_API_KEY` | Google API key for Gemini AI | Required |
| `VLLM_MODEL_NAME` | Gemini model name | gemini-2.5-flash |
| `SECRET_KEY` | JWT secret key | Change in production! |
| `GRAFANA_ENABLED` | Enable Grafana integration | true |

### Security Settings

- **Read-only access**: Configured to prevent DROP/DELETE/UPDATE operations
- **Rate limiting**: 100 requests per hour by default
- **Table restrictions**: Limit access to specific tables via `SNOWFLAKE_ALLOWED_TABLES`
- **Row limits**: Maximum 10,000 rows per query (configurable)
- **Query safety**: Automatic LIMIT addition for large result sets

## Project Structure

```
├── app/                    # Main application code
│   ├── agent/             # LangChain agent implementation
│   │   └── langchain_agent.py  # Real LangChain agent with tools
│   ├── auth/              # Authentication & security
│   ├── config/            # Configuration management
│   ├── integrations/      # External service integrations
│   │   ├── snowflake.py   # Snowflake connector
│   │   └── metrics.py     # Metrics collection
│   ├── tools/             # LangChain tools
│   │   └── snowflake_tool.py  # Snowflake query tools
│   └── models/            # Pydantic models
├── docker/                # Docker configurations
├── monitoring/            # Prometheus & Grafana configs
├── utils/                 # Utility scripts and requirements
├── example.env            # Environment template
├── .gitignore            # Git ignore rules
└── README.md             # This file
```

## Features

### LangChain Agent
- **Real LangChain implementation** with tools and memory
- **Gemini AI integration** for natural language processing
- **Tool-based architecture** for Snowflake interactions
- **Conversation memory** for context-aware responses

### Snowflake Tools
- **`get_table_names`**: List available tables
- **`get_table_schema`**: Get detailed table schema
- **`execute_snowflake_query`**: Execute SQL queries with safety limits

### Security & Safety
- Environment files with secrets are ignored by Git
- JWT-based authentication with configurable expiration
- CORS protection for web clients
- Rate limiting to prevent abuse
- SQL injection protection through parameterized queries
- Automatic query safety limits and validation

## API Endpoints

- `GET /` - Application status
- `GET /health` - Health check
- `POST /query` - Process natural language queries
- `GET /tables` - List available tables
- `GET /tables/{table}/schema` - Get table schema
- `GET /status` - Agent configuration status

## Usage Examples

### Natural Language Queries

```bash
# Get authentication token
python utils/simple_auth_token.py

# Query the agent
curl -X POST "http://localhost:8000/query" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "Show me the top 2 customers by total spending"}'
```

### Direct API Calls

```bash
# List tables
curl -X GET "http://localhost:8000/tables" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Get table schema
curl -X GET "http://localhost:8000/tables/customers/schema" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Development

### Adding New Features

1. Update models in `app/models/schemas.py`
2. Add endpoints in `app/main.py`
3. Implement business logic in `app/agent/` or `app/integrations/`
4. Add new tools in `app/tools/`
5. Add tests and update documentation

### Monitoring

The application includes comprehensive monitoring with:
- Prometheus metrics collection
- Grafana dashboards
- Health checks
- Performance tracking
- Error monitoring

## Architecture

The system uses a modern microservices architecture:

1. **FastAPI Application**: RESTful API server
2. **LangChain Agent**: Orchestrates AI interactions
3. **Gemini AI**: Natural language processing and SQL generation
4. **Snowflake Tools**: Secure database interactions
5. **Monitoring Stack**: Prometheus + Grafana for observability

## Troubleshooting

### Common Issues

1. **Authentication errors**: Ensure JWT token is valid and not expired
2. **Snowflake connection**: Verify credentials in `.env` file
3. **Gemini API errors**: Check `GOOGLE_API_KEY` is valid
4. **Query failures**: Review SQL syntax and table permissions

### Logs

```bash
# View application logs
docker compose -f docker/docker-compose.lightweight.yml logs -f snowflake-agent

# View specific service logs
docker compose -f docker/docker-compose.lightweight.yml logs snowflake-agent
```

