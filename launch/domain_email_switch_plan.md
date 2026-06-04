# GCA Domain Email Public Switch Plan

- Current public email: `support@gcagochina.com`
- Legacy email scanned: `GCAgochina@outlook.com`
- Target domain email: `support@gcagochina.com`
- Status: `public-email-switch-complete`
- Files requiring switch after activation: `0`

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

| File | Category | Legacy refs | Target refs | Action |
| --- | --- | ---: | ---: | --- |
| `docs/mainnet_public_profile.md` | project documentation | 0 | 2 | review target mention |
| `docs/whitepaper.md` | project documentation | 0 | 2 | review target mention |
| `launch/basescan_final_submission_package.json` | owner launch package | 0 | 6 | review target mention |
| `launch/basescan_final_submission_package.md` | owner launch package | 0 | 6 | review target mention |
| `launch/basescan_form_values.json` | owner launch package | 0 | 3 | review target mention |
| `launch/basescan_resubmission_package.md` | owner launch package | 0 | 5 | review target mention |
| `launch/basescan_resubmission_values.json` | owner launch package | 0 | 8 | review target mention |
| `launch/basescan_review_followup.md` | owner launch package | 0 | 5 | review target mention |
| `launch/basescan_reviewer_checklist.json` | owner launch package | 0 | 4 | review target mention |
| `launch/basescan_reviewer_checklist.md` | owner launch package | 0 | 4 | review target mention |
| `launch/basescan_token_submission.md` | owner launch package | 0 | 4 | review target mention |
| `launch/blockaid_false_positive_report.md` | owner launch package | 0 | 1 | review target mention |
| `launch/blockaid_followup_reply.md` | owner launch package | 0 | 1 | review target mention |
| `launch/data_platform_form_values.json` | owner launch package | 0 | 3 | review target mention |
| `launch/data_platform_package.md` | owner launch package | 0 | 2 | review target mention |
| `launch/domain_email_activation_runbook.md` | owner launch package | 0 | 23 | review target mention |
| `launch/domain_email_evidence_checklist.json` | owner launch package | 2 | 12 | review target mention |
| `launch/domain_email_evidence_checklist.md` | owner launch package | 2 | 11 | review target mention |
| `launch/domain_email_evidence_packet.json` | owner launch package | 0 | 10 | review target mention |
| `launch/domain_email_evidence_packet.md` | owner launch package | 0 | 5 | review target mention |
| `launch/domain_email_provider_matrix.json` | owner launch package | 0 | 17 | review target mention |
| `launch/domain_email_provider_matrix.md` | owner launch package | 0 | 8 | review target mention |
| `launch/domain_email_switch_plan.json` | owner launch package | 1 | 3 | review target mention |
| `launch/domain_email_switch_plan.md` | owner launch package | 1 | 3 | review target mention |
| `launch/external_review_followup_tracker.json` | owner launch package | 0 | 4 | review target mention |
| `launch/external_review_followup_tracker.md` | owner launch package | 0 | 8 | review target mention |
| `launch/geckoterminal_form_values.json` | owner launch package | 0 | 1 | review target mention |
| `launch/geckoterminal_update_runbook.md` | owner launch package | 0 | 3 | review target mention |
| `launch/launch_status.md` | owner launch package | 0 | 5 | review target mention |
| `launch/member_pre_registration_runbook.md` | owner launch package | 0 | 2 | review target mention |
| `launch/x_profile_runbook.md` | owner launch package | 0 | 3 | review target mention |
| `site/.well-known/gca-token.json` | well-known identity | 0 | 1 | review target mention |
| `site/.well-known/security.txt` | well-known identity | 0 | 1 | review target mention |
| `site/about.html` | public page | 0 | 3 | review target mention |
| `site/action-plan.html` | public page | 0 | 5 | review target mention |
| `site/announcements.html` | public page | 0 | 2 | review target mention |
| `site/announcements.json` | public structured data | 0 | 2 | review target mention |
| `site/basescan-handoff.html` | public page | 0 | 9 | review target mention |
| `site/basescan-handoff.json` | public structured data | 0 | 13 | review target mention |
| `site/basescan-preflight.html` | public page | 0 | 4 | review target mention |
| `site/basescan-preflight.json` | public structured data | 0 | 5 | review target mention |
| `site/basescan-remediation.html` | public page | 0 | 5 | review target mention |
| `site/basescan-remediation.json` | public structured data | 0 | 7 | review target mention |
| `site/blockaid-followup.json` | public structured data | 0 | 1 | review target mention |
| `site/brand-kit.json` | public structured data | 0 | 1 | review target mention |
| `site/community.html` | public page | 0 | 1 | review target mention |
| `site/community.json` | public structured data | 0 | 3 | review target mention |
| `site/daily-status.html` | public page | 0 | 4 | review target mention |
| `site/daily-status.json` | public structured data | 0 | 5 | review target mention |
| `site/domain-email-evidence.html` | public page | 0 | 15 | review target mention |
| `site/domain-email-evidence.json` | public structured data | 1 | 11 | review target mention |
| `site/domain-email.html` | public page | 0 | 31 | review target mention |
| `site/domain-email.json` | public structured data | 2 | 42 | review target mention |
| `site/external-reviews.html` | public page | 0 | 5 | review target mention |
| `site/external-reviews.json` | public structured data | 0 | 7 | review target mention |
| `site/gca/member-access/index.html` | public page | 0 | 4 | review target mention |
| `site/index.html` | public page | 0 | 2 | review target mention |
| `site/listing-kit.html` | public page | 0 | 2 | review target mention |
| `site/listing-readiness.html` | public page | 0 | 2 | review target mention |
| `site/listing-readiness.json` | public structured data | 0 | 2 | review target mention |
| `site/member-program.json` | public structured data | 0 | 1 | review target mention |
| `site/members.html` | public page | 0 | 2 | review target mention |
| `site/platform-replies.html` | public page | 0 | 2 | review target mention |
| `site/platform-replies.json` | public structured data | 0 | 2 | review target mention |
| `site/privacy.html` | public page | 0 | 5 | review target mention |
| `site/privacy.json` | public structured data | 0 | 2 | review target mention |
| `site/project-profile.html` | public page | 0 | 1 | review target mention |
| `site/project.json` | public structured data | 0 | 6 | review target mention |
| `site/register.html` | public page | 0 | 4 | review target mention |
| `site/release-gates.html` | public page | 0 | 1 | review target mention |
| `site/reviewer-kit.html` | public page | 0 | 3 | review target mention |
| `site/reviewer-kit.json` | public structured data | 0 | 8 | review target mention |
| `site/risk.html` | public page | 0 | 1 | review target mention |
| `site/roadmap.html` | public page | 0 | 1 | review target mention |
| `site/status.html` | public page | 0 | 1 | review target mention |
| `site/support.html` | public page | 0 | 2 | review target mention |
| `site/support.json` | public structured data | 0 | 1 | review target mention |
| `site/team.html` | public page | 0 | 1 | review target mention |
| `site/terms.html` | public page | 0 | 1 | review target mention |
| `site/token-safety.html` | public page | 0 | 1 | review target mention |
| `site/trust.html` | public page | 0 | 1 | review target mention |
| `site/trust.json` | public structured data | 0 | 4 | review target mention |
| `site/unsubscribe.html` | public page | 0 | 4 | review target mention |
| `site/verify.html` | public page | 0 | 1 | review target mention |
| `site/wallet-warning.html` | public page | 0 | 1 | review target mention |
| `site/wallet-warning.json` | public structured data | 0 | 1 | review target mention |
| `site/whitepaper.html` | public page | 0 | 3 | review target mention |
| `site/zh-access.html` | public page | 0 | 2 | review target mention |
| `site/zh-apply.html` | public page | 0 | 2 | review target mention |
| `site/zh-basescan-preflight.html` | public page | 0 | 8 | review target mention |
| `site/zh-basescan-submit.html` | public page | 0 | 6 | review target mention |
| `site/zh-cn.html` | public page | 0 | 2 | review target mention |
| `site/zh-domain-email.html` | public page | 0 | 19 | review target mention |
| `site/zh-faq.html` | public page | 0 | 4 | review target mention |
| `site/zh-member-checklist.html` | public page | 0 | 1 | review target mention |
| `site/zh-release-gates.html` | public page | 0 | 1 | review target mention |
| `site/zh-support.html` | public page | 0 | 4 | review target mention |
| `tools/gca_member_backend.py` | operator backend/tool | 0 | 1 | review target mention |

## Boundaries

- This plan does not change public files by itself.
- The patch preview is a generated diff only and does not write public files.
- This plan does not send email, write DNS, submit BaseScan requests, or touch wallets/contracts.
