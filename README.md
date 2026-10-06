# LLM API Audit Kit

**English** | [简体中文](README.zh-CN.md)

**LLM API evaluation, model fingerprinting, and token billing audits—with anonymized real-world results.**

A practical evaluation framework for AI procurement, third-party LLM API onboarding, and vendor management. It covers **pre-onboarding evaluation → post-onboarding checks → ongoing quality monitoring**.

> Detailed protocols, question banks, and case-study notes are currently primarily in Chinese. This README provides an English entry point.

## What it covers

| Area | Questions to investigate | Materials |
| --- | --- | --- |
| Capability and model consistency | Capability differences across providers, behavioral drift, and routing changes | 60-question comparison bank, behavioral and probability fingerprint protocols |
| Token billing | Unnecessary output, accounting differences, duplicate charges, and cost fluctuations | Dedicated token billing audit protocol |
| Service reliability | Latency, rate limits, peak-load behavior, and changes over time | Retesting and monitoring procedures |

## Get started

1. Read the [overall testing plan](docs/testing-plan.md) and define your evaluation stage and objectives.
2. Choose the [vendor comparison bank](docs/multi-vendor-question-bank.md), [behavioral fingerprint protocol](docs/behavior-fingerprint.md), [probability fingerprint protocol](docs/probability-fingerprint.md), or [token billing audit](docs/token-billing-audit.md).
3. Freeze the dataset version, parameters, model identifiers, and scoring rules. Retain original requests, responses, and billing evidence.
4. Document findings and human review using the [report template](templates/test-report.md) and [billing record fields](templates/billing-records.csv).

## Repository contents

| Path | Contents |
| --- | --- |
| [docs/](docs/testing-plan.md) | Overall plan, four detailed protocols, references, and known limitations |
| [examples/](examples/README.md) | Six original script attachments and a scoring example extracted from the documentation |
| [data/probability/](data/probability/README.md) | 743 original prompts and two example ground-truth whitelist entries |
| [case-studies/](case-studies/anonymized-evaluation/README.md) | Anonymized internal evaluation results and review records |
| [templates/](templates/test-report.md) | Blank report and billing record templates |
| [LICENSES/](LICENSES/Behavioral-Fingerprinting-MIT.txt) | Upstream behavioral fingerprinting copyright and license notice |

## Current status

**Real API testing completed internally · Anonymized results published · Further improvements underway**

The framework has been used in an internal enterprise evaluation of model onboarding and acceptance. The published [anonymized case study](case-studies/anonymized-evaluation/README.md) covers **6 test configurations, 4,758 primary test records, and 28 worksheets**, including scores, usage measurements, and anomaly reviews.

- **Test coverage:** Each configuration includes 21 behavioral probes, 743 probability-bank calls, and 29 token-usage tests. Selected configurations also have tool-use and LLMmap fingerprint records.
- **Recorded results:** Behavioral scores, request status, token usage, latency, anomalies, and retest conclusions. Company, provider, and internal identifiers have been anonymized.
- **Acceptance progress:** Initial evaluations and reviews are complete. Some configurations remain conditionally accepted or await end-to-end validation; consult the final review records for their scope.
- **Ongoing work:** Repeated probability sampling, consistent tool testing across configurations, threshold calibration, and resolution of accounting anomalies.

**Public code scope:** The repository includes reference scripts and original attachments. Some API integrations, answer whitelists, and scoring logic still require completion or adaptation. See the [code notes](examples/README.md) for implementation status and the case study for the internal execution records.

Interpret results alongside the [known limitations](docs/limitations.md). Fingerprints, capability scores, and token-count differences are signals for further investigation; they do not independently prove model identity or improper billing. See the [source inventory](docs/references.md) for included materials.

## Anonymized case study

The [historical evaluation results](case-studies/anonymized-evaluation/README.md) include per-question metrics, acceptance decisions, and anomaly reviews across 28 worksheets and 6 test configurations. Identifying information has been anonymized, and original free-text payloads have been withheld from the public export.

The results document the author's internal testing. They do not establish that the public reference scripts reproduce the entire internal workflow end to end; the documented code limitations still apply.

## Contributing

Issues and pull requests are welcome for completing rubrics, fixing reference scripts, and improving baselines and statistical methods. When changing prompts, ground truth, parameters, or scoring rules, record the version and its effect on existing baselines. Use anonymized examples and keep API keys and unauthorized business data out of submissions.

## Author and license

Framework author: **Mao Youqi (毛友琦)** · [maoyuki31-dev](https://github.com/maoyuki31-dev)

Original project documentation, question banks, and code are released under the [MIT License](LICENSE). Third-party research, probes, and derived material retain their respective rights and licenses; see [third-party notices](THIRD_PARTY_NOTICES.md). Research paper PDFs are not redistributed in this repository.
