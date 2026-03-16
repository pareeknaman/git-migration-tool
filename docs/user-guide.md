# User Guide

## Introduction
The Git Backup & Migration Web Tool provides an isolated, Dockerized interface for cloning and migrating Git repositories securely. 

## Modes
1. **Automated Migration**: Uses REST APIs to read repositories from GitHub, create a destination on GitLab, and perform a full mirror push.
2. **Platform-Agnostic Migration**: Can sync any two Git repositories via URLs using a standard bare clone and mirror push, injecting credentials so that it operates automatically without terminal prompts.

## Running Locally
Run `docker-compose up --build -d` and visit `http://localhost:8080`.
