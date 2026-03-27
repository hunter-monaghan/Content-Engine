# Security Policy

## Secrets and Credentials

Do not commit real credentials to this repository.

Protected by default:

- `.env`
- `.env.*` except `.env.example`
- certificate and private key files
- generated media in `output/`
- downloaded assets and local render artifacts
- Python bytecode and cache directories

Recommended practice:

1. Keep real API keys only in local `.env` files or a secret manager.
2. Rotate any key immediately if it is ever pasted into Git, logs, screenshots, or chat.
3. Use dedicated low-scope API keys for development when possible.
4. Treat generated metadata as publishable content and avoid embedding internal system data.

## Built-In Security Check

Run this before pushing:

```bash
python3 -m content_engine.main security-check
```

The check scans tracked project files for common secret patterns such as:

- OpenAI-style keys
- ElevenLabs keys
- generic bearer tokens
- API key assignments
- private key blocks

## GitHub Recommendations

Enable these repository settings:

1. Secret scanning
2. Push protection
3. Dependabot alerts
4. Branch protection on the default branch

## Reporting

If you find a leaked credential:

1. Revoke or rotate it first.
2. Remove it from the working tree and commit history if needed.
3. Re-run the security check.
4. Document the incident privately, not in a public issue.
