# Security policy

## Supported version

Security fixes are applied to the current `main` branch. Update before reporting a problem.

## Reporting a vulnerability

Use this repository's **Security → Report a vulnerability** button to contact the maintainer privately. Do not post credentials, `.env` files, project databases, process logs, or exploitable details in public issues. If private reporting is unavailable, open an issue asking for a private contact method without disclosing the vulnerability.

## Intended security boundary

Launchpad is a **single-user, local Windows development tool**. It intentionally executes the startup commands you enter with your Windows user permissions. It is **not a sandbox**, and it does not authenticate other applications or users already able to access your local machine.

- Both dashboard servers bind to loopback by default. Keep that binding.
- Host, Origin, Fetch Metadata, and a required custom request header help prevent a website from triggering launcher actions in your browser.
- Only loopback project URLs are accepted. Readiness checks verify that a listener belongs to the managed project process tree.
- Windows Job Objects and process creation times reduce accidental termination of unrelated processes.
- Runtime data, databases, logs, `.env` variants, private keys, and dependency folders are excluded from Git.
- Dependency scanning and tests help catch known issues; they are not a guarantee of vulnerability-free software.

Never expose the API using a public tunnel, port forwarding, `--host 0.0.0.0`, a shared server, or an unauthenticated reverse proxy. A remote or multi-user version needs separate authentication, authorization, CSRF protection, transport security, and process isolation design.

## Sharing safely

Share the **GitHub repository URL**, so others can clone the code and run their own local instance. Publishing this source code does not share your dashboard or give anyone control of your computer. A GitHub Pages site cannot run this Python process launcher.

Keep project commands free of embedded credentials. Child processes inherit your environment and can print sensitive values into their logs. Treat the local data directory as private; inspect any screenshot or diagnostic output before posting it.

The `X-Launchpad-Request: 1` header is an anti-CSRF marker, not a secret or authentication token. CLI clients must send it on POST/PUT/DELETE requests. Browser clients cannot add this custom header cross-origin without passing the server's CORS checks.
