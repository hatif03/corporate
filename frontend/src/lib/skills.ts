// Mirrors THIRD_PARTY_SKILLS.md's department->skill attribution table —
// real, curated data (not decorative), kept in sync by hand with that file.
// Surfaced in AgentDetailView's Skills tab so a department's persona is
// backed by something actually true about its prompt, not invented copy.

export interface SkillRef {
  stage: string
  skill: string
  author: string
  source: string
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
}
