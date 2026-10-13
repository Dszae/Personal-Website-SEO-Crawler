# Security Policy

## Supported versions

Only the latest version on the default branch is currently supported.

## Reporting a vulnerability

Please do not disclose exploitable details in a public issue. Contact the repository owner privately through the contact method listed on the GitHub profile. Include a clear description, reproduction steps, affected files or versions, and potential impact.

## Security design

The crawler is intentionally restricted to configured public domains, rejects non-HTTP schemes and private destinations, follows robots.txt by default, bounds responses and redirects, and treats fetched content as untrusted input. Do not use it against sites you do not own or have authorization to audit.
