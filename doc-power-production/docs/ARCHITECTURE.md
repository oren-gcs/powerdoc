# Doc-Power Architecture

## System Overview

Doc-Power is a microservices-based platform for enterprise document management.

### Components
- 7 Microservices
- MongoDB Database
- Redis Cache
- RabbitMQ Queue
- Kubernetes Orchestration
- Prometheus Monitoring
- Grafana Dashboards

## Deployment Architecture
- Production: Kubernetes cluster on EC2
- Staging: Kubernetes with Helm
- Development: Docker Compose
