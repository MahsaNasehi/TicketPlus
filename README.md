# TicketPlus: High-Demand Ticketing Platform

**TicketPlus** is a reference architecture and implementation for ticketing systems operating under high-demand scenarios. The project focuses on ensuring data consistency and system resilience without compromising domain invariants under peak loads.

---

## 🏗 System Architecture & Folder Structure

This system is built using **Microservices** and **Event-Driven Architecture** principles:

*   **Bounded Contexts:** Clear separation between Reservation, Checkout, and Event domains.
*   **Idempotency:** Strict processing guarantees to ensure duplicate requests do not corrupt system state.
*   **Asynchronous Messaging:** Event-driven synchronization for eventual consistency in ticket issuance.
*   **Resilience & Safety:** Prioritizing data safety over availability in ambiguous scenarios (e.g., preventing double-booking).

### Project Layout
*   `/src`: Core business logic and backend implementation (Python).
*   `/frontend`: Client-side UI and visualization page.
*   `/contracts`: API schemas (OpenAPI) and message/event schemas.
*   `/diagrams`: System design diagrams (Use-Case, Sequence, Component, Deployment).
*   `/docs`: Operational documents, incident management procedures, and postmortems.
*   `/infra`: Infrastructure as Code (Terraform configs for AWS EKS, RDS, MSK, Redis).

---

## 🚀 Execution & Quick Start Guide

Follow these steps to run and test the system locally:

### Prerequisites
*   Python 3.8+
*   A terminal interface

### Step 1: Run the Backend (Port 9090)
Execute the backend service using the following command:
```bash
cd ~/Desktop/New\ Folder/TicketPlus
PYTHONPATH=src DATABASE_PATH=./ticketplus.db PORT=9090 python3 -m ticketplus.http_api
