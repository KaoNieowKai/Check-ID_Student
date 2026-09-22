# Cloud Deployment & Infrastructure Requirements

This document outlines the technical specifications, architecture, and resource requirements for the **Student Activity Attendance System**. It is designed to assist infrastructure engineers and cloud architects in evaluating and selecting the most appropriate cloud provider (e.g., AWS, Google Cloud, Azure, DigitalOcean) for production deployment.

---

## 1. System Overview & Workload Characteristics

The system is a web-based application used by schools to manage student attendance via dynamic QR codes. 

**Traffic Pattern: Highly Spiky / Event-Driven**
* **Baseline Traffic:** Very low. Used occasionally by admins/teachers for setup and reporting.
* **Peak Traffic:** Extremely high, concentrated bursts. During an event check-in (e.g., 08:00 AM assembly), hundreds or thousands of students will scan the QR code and submit data simultaneously within a 5-15 minute window.
* **Concurrency:** The system heavily utilizes **WebSockets** for real-time dashboard updates (teachers watching the attendance count rise live).

---

## 2. Technology Stack

* **Backend Framework:** Python / FastAPI
* **Web Server (ASGI):** Uvicorn (Requires asynchronous execution support)
* **Frontend:** Server-side rendered HTML (Jinja2), Vanilla JS, CSS
* **Authentication:** JWT (JSON Web Tokens) with Bcrypt password hashing
* **Current Database:** SQLite (Used for local development only)
* **Production Database Requirement:** PostgreSQL or MySQL (Highly recommended for concurrent writes)

---

## 3. Infrastructure & Compute Requirements

### Compute (App Servers)
* **Execution Environment:** Containerization (Docker) is highly recommended. 
* **Scaling:** Must support **rapid Auto-Scaling**. The infrastructure must be able to spin up new instances quickly to handle sudden check-in spikes and scale down to zero/minimum to save costs during off-hours.
* **WebSocket Support:** The Load Balancer and compute instances MUST support long-lived WebSocket connections (WSS). Some serverless platforms have timeouts that drop WebSocket connections; this must be verified with the cloud provider.

### Database
* **Type:** Relational Database Management System (RDBMS).
* **Workload:** High concurrent `INSERT` and `UPDATE` operations during peak times.
* **Service Type:** A managed database service (e.g., Amazon RDS, Google Cloud SQL) is recommended to handle backups, high availability, and connection pooling.
* **Migration:** The application uses SQLAlchemy (ORM), making the transition from SQLite to PostgreSQL/MySQL seamless.

### Storage
* **Persistent Storage:** Very minimal. The application primarily deals with text data. Occasional Excel (`.xlsx`) file uploads for bulk student imports.
* **Object Storage (S3, etc.):** Not strictly required unless future requirements dictate storing student profile pictures or large exported reports asynchronously.

---

## 4. Security & Compliance Requirements

Because the system processes Student Personally Identifiable Information (PII) such as Names, IDs, and Class/Room data, the cloud architecture must prioritize security:

* **Data in Transit:** Full SSL/TLS encryption (HTTPS / WSS) is mandatory. Load balancers must terminate SSL.
* **Data at Rest:** The managed database must support encryption at rest.
* **Network Security (VPC):** The database should reside in a private subnet, inaccessible from the public internet. The application servers should be the only entities able to communicate with the database.
* **Environment Variables:** Secure secret management (e.g., AWS Secrets Manager, GCP Secret Manager) should be used to inject the `DATABASE_URL` and JWT `SECRET_KEY`.

---

## 5. Recommended Cloud Architectures

Based on the requirements, here are the viable deployment strategies to evaluate:

### Option A: Container-as-a-Service (CaaS) / Serverless Containers (Recommended)
* **Examples:** Google Cloud Run, AWS Fargate, Azure Container Apps.
* **Why:** Excellent for spiky workloads. They scale from zero to hundreds of instances in seconds and charge only for actual compute time used.
* **Checklist:** Ensure the chosen CaaS supports WebSockets effectively (e.g., Cloud Run supports WebSockets, but idle timeout configurations must be checked).

### Option B: Platform-as-a-Service (PaaS)
* **Examples:** Render, Heroku, DigitalOcean App Platform.
* **Why:** Simplest to deploy and manage for small developer teams. Built-in CI/CD, SSL, and managed databases.
* **Checklist:** May be slightly more expensive at scale, and auto-scaling rules might not be as aggressive/fast as needed for extreme traffic spikes.

### Option C: Traditional Auto-Scaling VMs / Kubernetes
* **Examples:** AWS EC2 Auto-scaling Groups + ALB, Google Kubernetes Engine (GKE).
* **Why:** Maximum control over networking, WebSocket timeouts, and connection limits.
* **Checklist:** Higher operational overhead. Requires dedicated DevOps effort to maintain the cluster and configure scaling policies.

---

## 6. Questions for Cloud Providers / Evaluation Criteria

When evaluating a cloud provider for this project, the infrastructure team should answer:
1. *How fast can the compute layer scale from 1 instance to 50 instances during a morning check-in rush?*
2. *Does the Load Balancer natively support WebSockets without abrupt timeouts?*
3. *What is the maximum concurrent connection limit on the managed database tier? Do we need an external connection pooler (like PgBouncer)?*
4. *What are the costs associated with idle time, since the system will likely sit idle 90% of the day?*
