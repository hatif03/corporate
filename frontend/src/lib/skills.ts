// Mirrors THIRD_PARTY_SKILLS.md's department->skill attribution table —
// real, curated data (not decorative), kept in sync by hand with that file.
// Surfaced in AgentDetailView's Skills tab so a department's persona is
// backed by something actually true about its prompt, not invented copy.

export interface SkillRef {
  stage: string
  skill: string
  /** Third-party adaptations have an author/source; original house skills
   * (no genuine third-party fit was found, see THIRD_PARTY_SKILLS.md) have
   * neither — the UI must not imply an attribution that doesn't exist. */
  author?: string
  source?: string
}

export const SKILLS_BY_DEPARTMENT: Record<string, SkillRef[]> = {
  engineering_sre: [
    { stage: 'triage', skill: 'diagnosing-bugs', author: 'Matt Pocock', source: 'https://github.com/mattpocock/skills' },
    { stage: 'cascade_predictor', skill: 'chaos-engineering', author: 'claude-code-skills', source: 'https://github.com/alirezarezvani/claude-skills' },
  ],
  finance_audit: [
    { stage: 'accountant', skill: 'financial-analyst', author: 'alirezarezvani', source: 'https://github.com/alirezarezvani/claude-skills' },
  ],
  marketing_comms: [
    { stage: 'brief_intake', skill: 'storybrand-messaging', author: 'wondelai', source: 'https://github.com/wondelai/skills' },
    { stage: 'copy_drafter', skill: 'copywriting', author: 'Corey Haines', source: 'https://github.com/coreyhaines31/marketingskills' },
  ],
  sales_crm: [
    { stage: 'lead_qualifier', skill: 'revops', author: 'Corey Haines', source: 'https://github.com/coreyhaines31/marketingskills' },
    { stage: 'outreach_drafter', skill: 'sales-enablement', author: 'Corey Haines', source: 'https://github.com/coreyhaines31/marketingskills' },
  ],
  legal_risk: [
    { stage: 'legal_compliance', skill: 'general-counsel-advisor', author: 'alirezarezvani', source: 'https://github.com/alirezarezvani/claude-skills' },
  ],
  executive: [
    { stage: 'cross_department_digest', skill: 'board-deck-builder', author: 'alirezarezvani', source: 'https://github.com/alirezarezvani/claude-skills' },
    { stage: 'announcement_drafter', skill: 'internal-comms', author: 'alirezarezvani', source: 'https://github.com/alirezarezvani/claude-skills' },
  ],
  // Original house skills — no genuine third-party fit was found for these
  // 3 departments' actual narrow tasks (see THIRD_PARTY_SKILLS.md for what
  // was checked and rejected), so these are this project's own, not
  // attributed to an external source.
  hr_people_ops: [{ stage: 'handbook_qa', skill: 'grounded-or-say-so' }],
  customer_support: [{ stage: 'response_drafter', skill: 'cite-or-escalate' }],
  product_analytics: [{ stage: 'metrics_analyst', skill: 'never-invent-a-number' }],
}
