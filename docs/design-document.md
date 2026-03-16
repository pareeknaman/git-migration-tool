# Design Document

## Architecture Overview
The application uses a standard Flask web server as the backend and a simple HTML/CSS frontend. It executes arbitrary Git commands using Python's `subprocess` module.

## Infrastructure
- **Docker**: The app runs in a customized Python container with native `git` installed.
- **Docker Compose**: Orchestrates the container, maps port 8080, and configures volume mounts for persisting backup archives locally.

## Security
Credentials are not logged to the console, and are securely passed via environment variables and injected automatically into Git clone/push URLs.
