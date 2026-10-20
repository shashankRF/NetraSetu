from .models import (
    AuthorityRequirement,
    DecisionImpact,
    EscalationLevel,
)


# ============================================================
# DECISION IMPACT SCORES
# ============================================================

IMPACT_SCORES = {

    DecisionImpact.INFORMATIONAL: 0,

    DecisionImpact.OPERATIONAL: 15,

    DecisionImpact.REGULATORY: 25,

    DecisionImpact.SECURITY: 30,

    DecisionImpact.SAFETY: 40,

    DecisionImpact.STRATEGIC: 45,
}


# ============================================================
# AUTHORITY HIERARCHY
#
# Higher number = higher authority
# ============================================================

AUTHORITY_LEVEL = {

    AuthorityRequirement.NONE: 0,

    AuthorityRequirement.ANALYST: 1,

    AuthorityRequirement.DOMAIN_EXPERT: 2,

    AuthorityRequirement.SENIOR_AUTHORITY: 3,
}


# ============================================================
# ESCALATION HIERARCHY
# ============================================================

ESCALATION_RANK = {

    EscalationLevel.AUTO_RESPONSE: 0,

    EscalationLevel.ANALYST_REVIEW: 1,

    EscalationLevel.DOMAIN_EXPERT: 2,

    EscalationLevel.SENIOR_AUTHORITY: 3,
}


def escalation_from_rank(
    rank: int,
) -> EscalationLevel:

    if rank <= 0:
        return EscalationLevel.AUTO_RESPONSE

    if rank == 1:
        return EscalationLevel.ANALYST_REVIEW

    if rank == 2:
        return EscalationLevel.DOMAIN_EXPERT

    return EscalationLevel.SENIOR_AUTHORITY