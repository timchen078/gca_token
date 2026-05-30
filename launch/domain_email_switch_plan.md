# GCA Domain Email Public Switch Plan

- Current email: `GCAgochina@outlook.com`
- Target domain email: `support@gcagochina.com`
- Status: `blocked-until-domain-email-evidence-ready`
- Files requiring switch after activation: `68`

## Required Preconditions

- support@gcagochina.com receives external email
- support@gcagochina.com sends authenticated external email
- MX, SPF, DKIM, and DMARC checks pass
- launch/domain_email_evidence_packet.json reports readyForBaseScanResubmission true
- tools/check_basescan_resubmission_readiness.py reports readyForBaseScanResubmission true

## Patch Preview

- Command: `python3 tools/build_domain_email_switch_plan.py --patch`
- Owner artifact: `python3 tools/build_domain_email_switch_plan.py --output-patch launch/domain_email_switch_preview.patch`
- The patch preview is an exact replacement diff only; it is not applied by this tool.

## Switch Order

1. Update public support and user-intake pages first.
2. Update public structured project/listing/reviewer JSON next.
3. Update BaseScan launch values and platform reply templates.
4. Run the full test suite and public site checker.
5. Submit one clean BaseScan update from the activated domain mailbox where possible.

## File Records

| File | Category | Current refs | Target refs | Action |
| --- | --- | ---: | ---: | --- |
| `docs/mainnet_public_profile.md` | project documentation | 1 | 0 | switch after evidence |
| `docs/whitepaper.md` | project documentation | 1 | 0 | switch after evidence |
| `launch/basescan_form_values.json` | owner launch package | 1 | 1 | switch after evidence |
| `launch/basescan_resubmission_package.md` | owner launch package | 2 | 1 | switch after evidence |
| `launch/basescan_resubmission_values.json` | owner launch package | 1 | 5 | switch after evidence |
| `launch/basescan_review_followup.md` | owner launch package | 2 | 2 | switch after evidence |
| `launch/basescan_reviewer_checklist.json` | owner launch package | 2 | 2 | switch after evidence |
| `launch/basescan_reviewer_checklist.md` | owner launch package | 2 | 2 | switch after evidence |
| `launch/blockaid_false_positive_report.md` | owner launch package | 1 | 0 | switch after evidence |
| `launch/blockaid_followup_reply.md` | owner launch package | 1 | 0 | switch after evidence |
| `launch/data_platform_form_values.json` | owner launch package | 3 | 0 | switch after evidence |
| `launch/data_platform_package.md` | owner launch package | 2 | 0 | switch after evidence |
| `launch/domain_email_activation_runbook.md` | owner launch package | 6 | 20 | switch after evidence |
| `launch/domain_email_evidence/README.txt` | owner launch package | 0 | 3 | review target mention |
| `launch/domain_email_evidence_checklist.json` | owner launch package | 2 | 11 | switch after evidence |
| `launch/domain_email_evidence_checklist.md` | owner launch package | 2 | 10 | switch after evidence |
| `launch/domain_email_provider_matrix.json` | owner launch package | 2 | 15 | switch after evidence |
| `launch/domain_email_provider_matrix.md` | owner launch package | 1 | 7 | switch after evidence |
| `launch/external_review_followup_tracker.json` | owner launch package | 1 | 0 | switch after evidence |
| `launch/external_review_followup_tracker.md` | owner launch package | 4 | 2 | switch after evidence |
| `launch/geckoterminal_form_values.json` | owner launch package | 1 | 0 | switch after evidence |
| `launch/geckoterminal_update_runbook.md` | owner launch package | 3 | 0 | switch after evidence |
| `launch/launch_status.md` | owner launch package | 2 | 0 | switch after evidence |
| `launch/member_pre_registration_runbook.md` | owner launch package | 2 | 0 | switch after evidence |
| `site/.well-known/gca-token.json` | well-known identity | 1 | 0 | switch after evidence |
| `site/.well-known/security.txt` | well-known identity | 1 | 0 | switch after evidence |
| `site/about.html` | public page | 2 | 0 | switch after evidence |
| `site/action-plan.html` | public page | 1 | 4 | switch after evidence |
| `site/basescan-handoff.html` | public page | 1 | 2 | switch after evidence |
| `site/basescan-handoff.json` | public structured data | 1 | 7 | switch after evidence |
| `site/basescan-preflight.html` | public page | 1 | 2 | switch after evidence |
| `site/basescan-preflight.json` | public structured data | 2 | 3 | switch after evidence |
| `site/basescan-remediation.html` | public page | 1 | 2 | switch after evidence |
| `site/basescan-remediation.json` | public structured data | 2 | 3 | switch after evidence |
| `site/blockaid-followup.json` | public structured data | 1 | 0 | switch after evidence |
| `site/brand-kit.json` | public structured data | 1 | 0 | switch after evidence |
| `site/daily-status.html` | public page | 1 | 2 | switch after evidence |
| `site/daily-status.json` | public structured data | 1 | 3 | switch after evidence |
| `site/domain-email-evidence.html` | public page | 4 | 12 | switch after evidence |
| `site/domain-email-evidence.json` | public structured data | 2 | 11 | switch after evidence |
| `site/domain-email.html` | public page | 4 | 21 | switch after evidence |
| `site/domain-email.json` | public structured data | 9 | 37 | switch after evidence |
| `site/external-reviews.html` | public page | 1 | 1 | switch after evidence |
| `site/external-reviews.json` | public structured data | 1 | 2 | switch after evidence |
| `site/index.html` | public page | 2 | 0 | switch after evidence |
| `site/listing-kit.html` | public page | 1 | 0 | switch after evidence |
| `site/member-program.json` | public structured data | 1 | 0 | switch after evidence |
| `site/members.html` | public page | 2 | 0 | switch after evidence |
| `site/platform-replies.html` | public page | 2 | 0 | switch after evidence |
| `site/platform-replies.json` | public structured data | 2 | 0 | switch after evidence |
| `site/privacy.html` | public page | 5 | 0 | switch after evidence |
| `site/privacy.json` | public structured data | 2 | 0 | switch after evidence |
| `site/project.json` | public structured data | 3 | 0 | switch after evidence |
| `site/register.html` | public page | 4 | 0 | switch after evidence |
| `site/reviewer-kit.html` | public page | 0 | 2 | review target mention |
| `site/reviewer-kit.json` | public structured data | 1 | 6 | switch after evidence |
| `site/status.html` | public page | 0 | 1 | review target mention |
| `site/support.html` | public page | 2 | 0 | switch after evidence |
| `site/support.json` | public structured data | 1 | 0 | switch after evidence |
| `site/trust.json` | public structured data | 1 | 3 | switch after evidence |
| `site/unsubscribe.html` | public page | 4 | 0 | switch after evidence |
| `site/wallet-warning.html` | public page | 1 | 0 | switch after evidence |
| `site/wallet-warning.json` | public structured data | 1 | 0 | switch after evidence |
| `site/whitepaper.html` | public page | 2 | 0 | switch after evidence |
| `site/zh-apply.html` | public page | 2 | 0 | switch after evidence |
| `site/zh-basescan-preflight.html` | public page | 2 | 5 | switch after evidence |
| `site/zh-cn.html` | public page | 2 | 0 | switch after evidence |
| `site/zh-domain-email.html` | public page | 6 | 18 | switch after evidence |
| `site/zh-faq.html` | public page | 2 | 0 | switch after evidence |
| `site/zh-status.html` | public page | 0 | 1 | review target mention |
| `site/zh-support.html` | public page | 4 | 0 | switch after evidence |
| `tools/gca_member_backend.py` | operator backend/tool | 1 | 0 | switch after evidence |

## Boundaries

- This plan does not change public files by itself.
- The patch preview is a generated diff only and does not write public files.
- This plan does not send email, write DNS, submit BaseScan requests, or touch wallets/contracts.
