# Product Importer

A scalable web application for importing products from CSV files (up to 500,000 records) into PostgreSQL with real-time progress tracking, product management UI, and webhook support.

![Product Importer](https://img.shields.io/badge/Python-3.11+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## 🚀 Features

- **CSV Import** - Upload large CSV files (up to 500K products) with real-time progress tracking
- **Product Management** - Full CRUD operations with filtering, pagination, and search
- **Webhook Support** - Configure webhooks for product events with testing capability
- **Bulk Operations** - Delete all products with confirmation protection
- **Real-time Updates** - SSE-based progress streaming for import status
- **Modern UI** - Dark theme, responsive design, smooth animations

## 🛠️ Tech Stack

- **Backend**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Task Queue**: Celery with Redis
- **Frontend**: Vanilla HTML/CSS/JavaScript
- **Deployment**: Docker + Render.com

## 📋 Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose (optional)

## 🏃‍♂️ Quick Start

### Using Docker Compose (Recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/product-importer.git
cd product-importer

# Start all services
docker-compose up -d

# Access the application
open http://localhost:8000
```

### Manual Setup

1. **Install dependencies**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Set environment variables**
```bash
cp .env.example .env
# Edit .env with your database and Redis URLs
```

3. **Start Redis and PostgreSQL**
```bash
# Using Docker
docker run -d -p 6379:6379 redis:7-alpine
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=product_importer postgres:15-alpine
```

4. **Start the application**
```bash
# Start web server
uvicorn app.main:app --reload

# In another terminal, start Celery worker
celery -A app.celery_app worker --loglevel=info
```

5. **Access the application**
```
http://localhost:8000
```

## 📁 CSV Format

Your CSV file should include the following columns:

| Column | Required | Description |
|--------|----------|-------------|
| sku | Yes | Unique product identifier (case-insensitive) |
| name | Yes | Product name |
| description | No | Product description |
| price | No | Price (decimal number) |
| quantity | No | Stock quantity (integer) |

### Example CSV

```csv
sku,name,description,price,quantity
PROD-001,Widget Pro,A professional widget,29.99,100
PROD-002,Gadget Plus,Enhanced gadget,49.99,50
PROD-003,Tool Basic,Standard tool,19.99,200
```

## 🔗 API Endpoints

### Products

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/products` | List products with pagination |
| POST | `/api/products` | Create a new product |
| GET | `/api/products/{id}` | Get product by ID |
| PUT | `/api/products/{id}` | Update a product |
| DELETE | `/api/products/{id}` | Delete a product |
| DELETE | `/api/products?confirm=true` | Delete all products |

### Imports

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/imports/upload` | Upload CSV file |
| GET | `/api/imports/{job_id}/status` | Get import status |
| GET | `/api/imports/{job_id}/stream` | SSE progress stream |
| GET | `/api/imports` | List import history |

### Webhooks

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/webhooks` | List webhooks |
| POST | `/api/webhooks` | Create webhook |
| PUT | `/api/webhooks/{id}` | Update webhook |
| DELETE | `/api/webhooks/{id}` | Delete webhook |
| POST | `/api/webhooks/{id}/test` | Test webhook |

## 🎯 Webhook Events

- `product.created` - Triggered when a product is created
- `product.updated` - Triggered when a product is updated
- `product.deleted` - Triggered when a product is deleted
- `import.started` - Triggered when import begins
- `import.completed` - Triggered when import completes
- `import.failed` - Triggered when import fails

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Web Browser   │────▶│   FastAPI       │────▶│   PostgreSQL    │
│                 │◀────│   (Web Server)  │◀────│                 │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                                 │ SSE
                                 │
                        ┌────────▼────────┐
                        │     Redis       │
                        │   (Broker)      │
                        └────────┬────────┘
                                 │
                        ┌────────▼────────┐
                        │     Celery      │
                        │   (Workers)     │
                        └─────────────────┘
```

## 🚀 Deployment

### Render.com

1. Fork this repository
2. Connect to Render.com
3. Create new Blueprint from `render.yaml`
4. Deploy!

### Other Platforms

The application can be deployed to any platform supporting Docker:
- AWS (ECS, EKS)
- Google Cloud (Cloud Run, GKE)
- Heroku (with worker dyno for Celery)
- DigitalOcean (App Platform)

## 📊 Performance Optimizations

- **Chunked Processing**: CSV files processed in 5,000-row batches
- **Bulk Upserts**: PostgreSQL `ON CONFLICT` for efficient updates
- **Progress Streaming**: SSE for real-time updates without polling
- **Memory Efficient**: Streaming CSV processing, no full file loading
- **Connection Pooling**: SQLAlchemy pool for database connections

## 🧪 Testing

```bash
# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

## 📝 License

MIT License - feel free to use this project for any purpose.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
