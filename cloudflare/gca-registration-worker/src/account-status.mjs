const STATUS_ACCESS_TOKEN_RE = /^gca_status_[A-Za-z0-9_-]{43}$/;

export function isStatusAccessToken(value) {
  return STATUS_ACCESS_TOKEN_RE.test(String(value || "").trim());
}

export function maskWalletAddress(value) {
  const wallet = String(value || "").trim().toLowerCase();
  if (!/^0x[a-f0-9]{40}$/.test(wallet)) {
    return "";
  }
  return `${wallet.slice(0, 8)}...${wallet.slice(-4)}`;
}

export function buildPublicAccountStatus({
  account,
  walletVerification,
  creditLedger,
  memberLedger,
  checkedAt,
  nextStep
}) {
  const verification = walletVerification || null;
  const credit = creditLedger || null;
  const member = memberLedger || null;
  return {
    checkedAt,
    account: account
      ? {
          accountId: account.accountId,
          status: account.status,
          walletAddressMasked: maskWalletAddress(account.walletAddress),
          createdAt: account.createdAt,
          updatedAt: account.updatedAt
        }
      : null,
    walletVerification: verification
      ? {
          walletVerificationId: verification.walletVerificationId,
          checkedAt: verification.checkedAt,
          gcaBalance: verification.gcaBalance,
          holderBonusEligible: Boolean(verification.holderBonusEligible),
          gcaMemberEligible: Boolean(verification.gcaMemberEligible),
          holdingPeriodDaysVerified: Number(verification.holdingPeriodDaysVerified || 0),
          status: verification.status
        }
      : null,
    creditLedger: credit
      ? {
          creditLedgerId: credit.creditLedgerId,
          creditAmount: Number(credit.creditAmount || 0),
          remainingCredits: Number(credit.remainingCredits || 0),
          activatedAt: credit.activatedAt,
          expiresAt: credit.expiresAt,
          status: credit.status
        }
      : null,
    memberLedger: member
      ? {
          memberLedgerId: member.memberLedgerId,
          tierName: member.tierName,
          verifiedBalance: member.verifiedBalance,
          holdingPeriodDaysVerified: Number(member.holdingPeriodDaysVerified || 0),
          memberBenefitReviewEvidenceStatus: member.memberBenefitReviewEvidenceStatus,
          memberBenefitAmount: member.memberBenefitAmount,
          memberBenefitClaimStatus: member.memberBenefitClaimStatus,
          memberBenefitTransferTx: member.memberBenefitTransferTx,
          memberBenefitTransferVerifiedAt: member.memberBenefitTransferVerifiedAt,
          memberBenefitTransferVerificationStatus: member.memberBenefitTransferVerificationStatus,
          activatedAt: member.activatedAt,
          nextRefreshDueAt: member.nextRefreshDueAt,
          onchainHoldingVerified: Boolean(member.onchainHoldingVerified),
          onchainHoldingVerifiedAt: member.onchainHoldingVerifiedAt,
          status: member.status,
          updatedAt: member.updatedAt
        }
      : null,
    nextStep,
    boundaries: {
      readOnlyStatusLookup: true,
      emailReturned: false,
      accessTokenReturned: false,
      adminTokenRequired: false,
      requiresSignature: false,
      requiresTransaction: false,
      automaticTokenTransfer: false
    }
  };
}
