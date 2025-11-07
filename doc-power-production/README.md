# Doc-Power: Enterprise Document Management System

[![GitHub License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.0.0-brightgreen.svg)](VERSION)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![Kubernetes](https://img.shields.io/badge/kubernetes-1.27+-blue.svg)](https://kubernetes.io)

Production-grade microservices platform for document management with OCR capabilities, workflow automation, and enterprise-grade monitoring.

## 🚀 Quick Start (Local Development)

This is the fastest way to get all services running on your machine.

1.  **Install Prerequisites:**
    * Docker & Docker Compose

2.  **Create Environment File:**
    * Copy the `.env.example` to a new file named `.env`.
    * `cp .env.example .env`
    * (Optional) Open `.env` and change the default passwords (like `MONGODB_PASSWORD` and `REDIS_PASSWORD`).

3.  **Start All Services:**
    * `make docker-up`

4.  **Check Services:**
    * Wait about 30-60 seconds for services to start.
    * Open your browser or use `curl`:
    * `curl http://localhost:8001/health` (API Gateway)
    * `curl http://localhost:8002/health` (Auth Service)

5.  **Access Monitoring Dashboards:**
    * **Grafana:** `http://localhost:3000` (admin/admin)
    * **Prometheus:** `http://localhost:9090`
    * **RabbitMQ:** `http://localhost:15672` (guest/guest)

6.  **Stop Services:**
    * `make docker-down`

## 📊 Architecture

```
Client Requests
    ↓
API Gateway (8001)
    ↓
├─ Auth Service (8002)
├─ Document Service (8003)
├─ OCR Service (8004)
├─ Workflow Service (8005)
├─ Notification Service (8006)
└─ Analytics Service (8007)
    ↓
├─ MongoDB (Data)
├─ Redis (Cache)
├─ RabbitMQ (Queue)
└─ N8N (Workflows)
    ↓
Monitoring (Prometheus/Grafana)
```

## 🔧 Services

| Service | Port | Internal Port | Purpose |
|---------|:----:|:-------------:|---------|
| API Gateway | 8001 | 8000 | Central entry point |
| Auth Service | 8002 | 8000 | Authentication & RBAC |
| Document Service | 8003 | 8000 | Document management |
| OCR Service | 8004 | 8000 | AWS Textract integration |
| Workflow Service | 8005 | 8000 | N8N orchestration |
| Notification Service | 8006 | 8000 | Email/SMS alerts |
| Analytics Service | 8007 | 8000 | Metrics & reporting |

## 🧪 Testing

```bash
# Run all tests
make test

# Run unit tests
make test-unit

# Run integration tests
make test-integration

# Generate coverage report
make coverage
```
