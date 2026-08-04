# Security policy

## Supported versions

The latest tagged release receives security fixes.

## What BenchLineage protects

Evidence seals detect changes to inventoried bytes. Path normalization prevents a run record from
referencing a raw file outside the workspace. HTML reports escape user-controlled labels and
embed no third-party scripts.

## What it does not protect

BenchLineage is not an access-control system, secret store, backup product, trusted timestamp
authority, or digital-signature service. Anyone who can modify both evidence and its seal can
create a new internally consistent seal. Use operating-system permissions, versioned remote
storage, and institutional controls where the threat model requires them.

Do not place passwords, API keys, unpublished personal information, export-controlled material,
or sensitive participant data in a public workspace.

## Reporting a vulnerability

Open a private security advisory through the repository's **Security** tab. Include the affected
version, minimal reproduction, impact, and any proposed mitigation. Please do not publish an
unfixed vulnerability in a public issue.
