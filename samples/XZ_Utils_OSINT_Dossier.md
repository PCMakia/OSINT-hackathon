# OSINT Intelligence Dossier: XZ Utils Backdoor (CVE-2024-3094)

**Target key:** `xz utils backdoor`  
**Collection:** Extracted from local `cache.json` (Wikipedia, Tukaani/Jia Tan note, CISA-class advisories, engineering write-ups) plus seeded oss-security / NVD timeline fixtures.  
**Mode:** Sample export for offline / non-Discord evaluation.

## Executive Summary

CVE-2024-3094 is a **supply-chain backdoor in XZ Utils 5.6.0 and 5.6.1** (liblzma), discovered by **Andres Freund** (29 March 2024) while debugging Debian unstable. Malicious artifacts in the **Jia Tan–signed upstream tarballs** were built into `liblzma` and, on systemd-based Linux distributions, could interfere with **OpenSSH sshd** so that an attacker holding a **specific private key** could bypass authentication / achieve pre-auth command execution. This is a **maintainer-trust failure** (multi-year “Jia Tan” social engineering against original maintainer Lasse Collin), not a random host implant.

## ⚠️ Contradiction & Discrepancy Alert

> **Primary technical reporting** (oss-security / Freund; Wikipedia synthesis; Puppet; SentinelOne) agrees on *what shipped*: obfuscated test objects in 5.6.0/5.6.1 tarballs, `liblzma` modification, sshd impact via glibc `ifunc` resolvers. **Impact language diverges by source type:** some describe a **designated-key authentication bypass**; others say **remote code execution** or **admin-level access before SSH authentication**. **Tukaani.org** (original maintainer) emphasizes provenance — tarballs **created and signed by Jia Tan**, vs tarballs signed by Lasse Collin — rather than exploit mechanics. **NVD / secondary timeline** pieces add the 2021–2022 contributor-to-maintainer arc; that social-engineering chronology is **medium-confidence synthesis**, not a CVE field. Do not collapse “ssh bypass,” “RCE,” and “LandLock disable follow-on” into a single uncited claim.

## Form Factor & Technical Specs Matrix

| Dimension | Subject Device | Comparison Notes |
| --- | --- | --- |
| Display / Form Factor | Not a hardware product. Artifact is **XZ Utils / liblzma** compression library in Linux distro packages | Contrast with hardware OSINT dossiers; “form factor” here is **upstream tarball + distro build** |
| AI Engine | Not applicable. Payload used **glibc ifunc resolvers** (`crc32_resolve` / `crc64_resolve`) to swap in malicious implementations at runtime | Indirect execution via library load into **sshd**, not a standalone malware binary users launch |
| Latency | Discovery latency: backdoor sat in 5.6.0/5.6.1 until Freund’s Debian investigation (public 2024-03-29). Exploitation requires the attacker key and a vulnerable sshd/liblzma pairing | Social-engineering timeline is **years**; technical dwell in released tarballs is **weeks-to-months** |
| Power / Connectivity | High-value path: **sshd** on systemd Linux that pulls compromised `liblzma`. OpenSSH does not normally depend on XZ; the implant **creates** that linkage in affected builds | Operators: downgrade to **5.4.x**, audit for 5.6.0/5.6.1, treat Jia Tan–signed tarballs as untrusted |

## Competitive Positioning

- **Vs typical CVEs:** This is a **trusted-upstream implant**, not a memory-corruption bug in a random daemon. Comparisons belong with **SolarWinds-class supply chain** more than with routine OpenSSH CVEs.
- **Vs other OSS social-engineering:** OpenSSF / OpenJS warned the pattern (persistent, friendly pressure for maintainer rights) may not be isolated — relevant to JavaScript/foundation-hosted projects, not only compression libraries.
- **Vs later xz commits:** SentinelOne notes follow-on work (LandLock disable, extra test-binary execution in 5.6.1) suggesting the actor **planned additional implants**, not a one-shot sshd hook.
- **Response baseline:** Distros and CISA-class alerts: **remove 5.6.0/5.6.1**, revert to 5.4.x lineage, verify maintainer signatures (Collin vs Jia Tan).

## Source Credibility & Verification Tier

| Source URL | Type | Credibility Rating | Rationale |
| --- | --- | --- | --- |
| https://www.openwall.com/lists/oss-security/2024/03/29/4 | PR | High | Seeded primary: Freund oss-security notice (liblzma injection, sshd bypass framing) |
| https://www.cisa.gov/news-events/alerts/2024/03/29/reported-supply-chain-compromise-affecting-xz-utils-data-compression-library-cve-2024-3094 | PR | High | Official US advisory: supply-chain, 5.4.x downgrade, systemd/sshd exposure |
| https://tukaani.org/xz-backdoor | PR | High | Upstream maintainer page: CVE-2024-3094, Jia Tan signed 5.6.0/5.6.1 tarballs |
| https://en.wikipedia.org/wiki/XZ_Utils_backdoor | Bench | Medium | Secondary encyclopedia synthesis; useful chronology, not a primary advisory |
| https://www.puppet.com/blog/xz-backdoor | Bench | Medium | Engineering explainer: sshd pre-auth command execution |
| https://www.sentinelone.com/blog/xz-utils-backdoor-threat-actor-planned-to-inject-further-vulnerabilities | Leak | Medium | Industry analysis: ifunc, LandLock, planned further vulns |
| https://nvd.nist.gov/vuln/detail/CVE-2024-3094 | Bench | Medium | Seeded NVD/timeline fixture: Jia Tan multi-year maintainer pressure |
| https://www.wilsoncenter.org/blog-post/how-secure-open-source-software-dilemma-xz-utils-backdoor | Bench | Medium | Policy/OSS-process commentary, not exploit primary source |
