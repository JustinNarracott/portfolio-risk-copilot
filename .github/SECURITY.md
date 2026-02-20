# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.2.x   | ✅ Current |
| < 1.2   | ❌ Not supported |

## Reporting a Vulnerability

If you discover a security vulnerability in Portfolio Risk Copilot, please report it responsibly.

**Do not open a public GitHub issue for security vulnerabilities.**

Instead, email **justin@signalbreak.io** with:

- A description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if you have one)

You should receive a response within 48 hours. We'll work with you to understand and address the issue before any public disclosure.

## Scope

This tool runs entirely locally — your project data never leaves your machine. However, security concerns could include:

- **Path traversal** during file ingestion (reading files outside the intended folder)
- **Code injection** via crafted CSV/JSON/Excel files
- **Denial of service** via extremely large input files

## Data Privacy

Portfolio Risk Copilot is designed as a local-first tool. It does not:

- Send data to any external server
- Store data outside the user's working directory
- Require network access to function
- Collect telemetry or usage analytics

All processing happens on the user's machine via Claude Cowork or CLI.
