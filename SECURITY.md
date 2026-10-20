# Security Policy

## Overview

HackGrid is an evidence-grounded, jurisdiction-aware AI framework for technical, regulatory, security, and research analysis.

Because HackGrid may process security-related and regulatory information, security, provenance, and responsible handling of information are important parts of the project.

## Supported Versions

| Version | Supported |
|---------|-----------|
| v1.0.x | Yes |
| Older versions | No |

## Reporting a Security Vulnerability

Please do not publicly disclose security vulnerabilities through GitHub Issues or Pull Requests.

Security vulnerabilities should be reported privately to the project maintainer.

Please include:

- Description of the vulnerability
- Affected component or file
- Steps to reproduce
- Potential security impact
- Suggested mitigation, if known

Do not include API keys, passwords, authentication tokens, or other secrets in vulnerability reports.

## Secrets and Credentials

HackGrid uses environment-based configuration for sensitive credentials.

API keys and secrets must:

- Never be committed to the repository
- Never be embedded in frontend code
- Never be included in screenshots or demonstrations
- Be stored in local environment configuration
- Be rotated immediately if accidentally exposed

The project's .env file is excluded from version control.

## Knowledge Base and Evidence Security

HackGrid distinguishes between:

- Real knowledge-base evidence
- Retrieved evidence
- Simulated scenario data
- AI-generated analysis

Simulated scenarios must not be represented as real-world evidence.

Retrieved evidence should retain appropriate provenance and source metadata wherever supported by the system.

## AI and Governance

HackGrid follows these principles:

> AI recommends. Evidence supports. Risk Engine determines governance requirements. Human authority makes consequential decisions.

The AI system must not:

- Grant itself authority
- Approve its own output
- Bypass mandatory human review
- Fabricate evidence, regulations, standards, or citations
- Remove or downgrade governance requirements
- Fabricate human approval

High-impact decisions should remain subject to the project's Risk & Authority and Human Review mechanisms.

## Responsible Disclosure

Security researchers are encouraged to report vulnerabilities privately so that issues can be investigated and addressed appropriately.

## Scope

This policy applies to the HackGrid source code and associated project infrastructure maintained in this repository.

Third-party services used by HackGrid may have their own security and vulnerability-reporting policies.

## Disclaimer

HackGrid is an evolving research and prototype project.

It should not be treated as a substitute for professional cybersecurity, regulatory, legal, safety, or operational decision-making.

Users remain responsible for independently validating consequential decisions and ensuring compliance with applicable requirements.
