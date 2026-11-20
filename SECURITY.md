# Security policy

## Reporting a problem

Found a security issue in one of these apps, the shop or Free Lane? Please report it privately:

- **Help form:** https://shop.frantzmichaelsthilairevardman.com/support/ (choose "Security problem")
- **Email:** frantzvardman@mail2one.com

Please include the app and version, your phone model and Android version, and the steps to reproduce. Don't open a public issue for security problems, and please give a reasonable amount of time for a fix before sharing details.

## What's in scope

- The Android apps listed in this repository and their update checks
- Free Lane (the app store) and its download and fingerprint checks
- The shop at https://shop.frantzmichaelsthilairevardman.com

## How releases are protected

- Every app is built by GitHub Actions from source and signed with its own release key; Free Lane checks each download's fingerprint before installing.
- App files are served only to signed-in accounts from a private vault.
- The apps contain no third-party analytics or ad SDKs.

Thank you for helping keep people safe.
