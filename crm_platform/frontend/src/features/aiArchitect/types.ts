export type AiArchitectMessage = {
  id: string
  sender: string
  content: string
}

export type AiArchitectBlueprint = {
  id: string
  version: string
  blueprint: {
    business_summary: string
    business_profile: string
    departments: string[]
    roles: string[]
    entities: string[]
    forms: string[]
    reports: string[]
    assumptions: string[]
  }
}

export type AiArchitectProposal = {
  id: string
  proposal_type: string
  operation: 'create' | 'update'
  title: string
  description: string
  rationale: string
  generated_artifacts: Array<{ type: string; name: string }>
  applied_artifacts: Array<{ type: string; name: string; id: string }>
  target_artifacts: Array<{ type: string; name: string; id: string }>
  before_state: Record<string, unknown>
  after_state: Record<string, unknown>
  risk_level: 'low' | 'medium' | 'high'
  status: string
}

export type AiArchitectConversation = {
  id: string
  title: string
  status: string
  messages: AiArchitectMessage[]
  blueprint: AiArchitectBlueprint | null
  proposals: AiArchitectProposal[]
}

export type AiArchitectChangeEvent = {
  id: string
  operation: string
  affected_artifacts: Array<{ type: string; name: string; id: string }>
  before_state: Record<string, unknown>
  after_state: Record<string, unknown>
  rollback_status: 'available' | 'rolled_back' | 'unavailable'
  rollback_reason: string | null
  created_at: string | null
  rolled_back_at: string | null
}
