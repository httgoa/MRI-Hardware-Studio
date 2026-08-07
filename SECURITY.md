# Security Policy

## Supported Versions

| Version | Supported |
|---|---|
| latest (main branch) | ✅ |

## Reporting a Vulnerability

If you discover a security vulnerability in MRI Hardware Studio (e.g., in the Python scripts or MCP server integration), please do **not** open a public GitHub Issue.

Instead, please report it by emailing the repository maintainers directly (contact information is available in the GitHub repository's About section) or by opening a private security advisory via the GitHub Security tab.

We will acknowledge the report within 48 hours and aim to provide a fix or mitigation within 14 days.

## Scope

This project's security surface is limited to:
- Python scripts in `skills/mri-coil-design-workflow/scripts/`
- Any configuration files that may handle paths or environment variables

This project does **not** handle user authentication, network services, or sensitive user data. The CST Studio Suite COM interface runs locally on the user's machine.
