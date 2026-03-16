# Project Title: Git Backup & Migration Web Tool

**Student Name:** Naman Pareek
**Registration No:** 23FE10CSE00706
**Course:** CSE3253 DevOps [PE6]
**Semester:** VI (2025-2026)
**Project Type:** Backup Automation & CI/CD
**Difficulty:** Intermediate

---

## Project Overview

### Problem Statement
Relying on a single version control provider creates a single point of failure and vendor lock-in. This project provides an automated, containerized solution to mirror repositories across platforms, acting as both a migration utility and a hot off-site backup.

### Objectives
- Automate bare cloning and mirror pushing via REST APIs.
- Containerize the complete application environment using Docker.
- Implement a continuous integration and deployment (CI/CD) pipeline for automated testing and builds.

### Key Features
- **Dual-mode web interface**: 
  - Automated GitHub-to-GitLab extraction mode.
  - Platform-Agnostic manual URL mode.
- **Real-time UI logging**: Monitor Git subprocess output directly in the browser via Server-Sent Events.
- **Secure cold backups**: Automatic local `.tar.gz` archive creation on success.

---

## Technology Stack

- **Python 3 (Flask)**
- **Git**
- **Docker & Docker Compose**
- **GitHub Actions (CI/CD)**

---

## Getting Started

### Prerequisites
- Docker Desktop
- Git

### Installation & Run

1. Clone the project repository:
   ```bash
   git clone <your-repository-url>
   cd DevOps_Project/git_migration_tool
   ```

2. Create the environment configuration file:
   ```bash
   touch .env
   ```
   *(See Configuration section below for details)*

3. Build and execute the Docker container:
   ```bash
   docker-compose up --build -d
   ```

4. Access the web interface: Open your browser and navigate to `http://localhost:8080`.

---

## Configuration

The application requires a `.env` file at the root of the project to securely read API tokens. Here is an example of the structure:

```env
# Example .env configuration

GITHUB_TOKEN=ghp_your_github_personal_access_token_here
GITHUB_OWNER=your_github_username

GITLAB_TOKEN=glpat-your_gitlab_personal_access_token
GITLAB_NAMESPACE=your_optional_gitlab_group_or_username
```

---

## CI/CD Pipeline & Docker

### GitHub Actions
A defined CI/CD pipeline (`pipelines/.github/workflows/ci-cd.yml`) has been established. On every push or pull request to the `main` branch, the pipeline automatically:
1. Sets up the Python environment.
2. Checks syntax and lints the code using `flake8`.
3. Executes unit tests via `pytest`.
4. Builds the Docker image `git-migration-tool:latest` to ensure environment consistency.

### Docker Environment
The application is wrapped within a customized Python slim image that pre-installs the native `git` CLI package.

Key Docker commands utilized within the scope of this project:
- `docker build -t git-migration-tool:latest -f infrastructure/docker/Dockerfile .`
- `docker-compose up --build -d`
- `docker-compose down`

---

## Demo

- [Project Presentation (Google Slides)](https://docs.google.com/presentation/d/1oX3I6quGHMyU71-AqB8TD2t2o7keUZRB/edit?usp=sharing&ouid=117040861685677662204&rtpof=true&sd=true)
- [Project Demo Video (Google Drive)](https://drive.google.com/file/d/1X0NVRLusSTfOgPKuIopd8qXubbg2lGOQ/view?usp=sharing)
