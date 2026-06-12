# Security Policy

Thank you for helping keep Semantic Platform Template and its users safe. This
policy explains which versions receive security updates and how to report a
vulnerability responsibly.

## Supported Versions

This repository is a template intended to be adapted by downstream projects.
Security fixes are provided on the default branch and in the most recent tagged
release, when releases are available.

| Version | Supported |
| --- | --- |
| Default branch | Yes |
| Latest release | Yes |
| Older releases | No, unless explicitly documented in release notes |

Downstream projects should maintain their own version support matrix after
forking or generating an implementation from this template.

## Reporting a Vulnerability

Please do not open public issues, pull requests, discussions, or comments for
suspected security vulnerabilities.

Report vulnerabilities by creating a private security advisory in GitHub if it is
enabled for the repository. If private advisories are not available, contact the
maintainers through the repository owner's preferred private contact channel and
include `SECURITY` in the subject line.

Include as much detail as you safely can:

- Affected component, file, route, script, or configuration.
- Steps to reproduce or a proof of concept.
- Expected and observed impact.
- Required privileges, user interaction, or deployment assumptions.
- Suggested remediation, if known.

## Response Expectations

Maintainers should acknowledge valid reports within 5 business days. After
acknowledgement, maintainers will triage the report, estimate severity, and share
next steps or additional information requests as soon as practical.

If a report is accepted, maintainers will coordinate a fix before public
disclosure whenever possible. Public disclosure should include a summary of the
impact, affected versions, remediation guidance, and credit when the reporter
wants attribution.

## Security Update Process

For accepted vulnerabilities, maintainers should:

1. Reproduce and document the issue privately.
2. Identify affected supported versions.
3. Prepare and review the smallest safe fix.
4. Run the repository verification checks before release.
5. Publish remediation guidance, including upgrade or configuration steps.

## Scope

In scope:

- Vulnerabilities in repository code, scripts, Docker assets, RDF assets, or
  default configuration.
- Weak defaults that could expose credentials, sensitive data, or administrative
  capabilities.
- Supply-chain risks introduced by project-managed dependencies or build files.

Out of scope:

- Vulnerabilities in unsupported downstream forks or private customizations.
- Denial-of-service reports that rely only on unrealistic resource exhaustion.
- Social engineering or physical attacks.
- Findings that require already-compromised maintainer credentials.

## Handling Sensitive Data

Do not include secrets, production data, personal data, or full database dumps in
reports. If sensitive data is necessary to demonstrate impact, provide the
minimum redacted sample required to reproduce the issue.
