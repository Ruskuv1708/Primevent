import { useEffect, useState, type FormEvent } from 'react'
import axios from 'axios'
import { useNavigate } from 'react-router-dom'
import theme from '../../shared/theme'
import { useI18n } from '../../shared/i18nContext'
import { normalizeRole, roleMatches } from '../../shared/roleLabels'
import type {
  AiArchitectChangeEvent,
  AiArchitectConversation,
  AiArchitectProposal,
} from './types'

function AiArchitectPage() {
  const [conversation, setConversation] = useState<AiArchitectConversation | null>(null)
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [refining, setRefining] = useState(false)
  const [history, setHistory] = useState<AiArchitectChangeEvent[]>([])
  const [error, setError] = useState('')
  const navigate = useNavigate()
  const { language, t } = useI18n()

  const token = localStorage.getItem('crm_token')

  useEffect(() => {
    ;(async () => {
      if (!token) {
        navigate('/')
        return
      }

      try {
        const userRes = await axios.get('/access/me', {
          headers: { Authorization: `Bearer ${token}` },
        })
        if (!roleMatches(normalizeRole(userRes.data.role), ['SUPERADMIN', 'SYSTEM_ADMIN', 'ADMIN'])) {
          navigate('/home')
          return
        }
        const res = await axios.post<AiArchitectConversation>(
          '/ai-architect/conversations',
          { title: 'AI CRM Architect' },
          { headers: { Authorization: `Bearer ${token}` } },
        )
        setConversation(res.data)
        const historyRes = await axios.get<AiArchitectChangeEvent[]>(
          '/ai-architect/change-events',
          { headers: { Authorization: `Bearer ${token}` } },
        )
        setHistory(historyRes.data)
      } catch (err: any) {
        setError(err?.response?.data?.detail || t('ai.failedStart'))
      } finally {
        setLoading(false)
      }
    })()
  }, [navigate, token])

  const sendMessage = async (event: FormEvent) => {
    event.preventDefault()
    if (!token || !conversation || !message.trim()) return

    setSending(true)
    setError('')
    try {
      const res = await axios.post(
        `/ai-architect/conversations/${conversation.id}/messages`,
        { content: message.trim() },
        { headers: { Authorization: `Bearer ${token}` } },
      )
      setConversation(prev => prev
        ? { ...prev, messages: [...prev.messages, res.data] }
        : prev)
      if (conversation.blueprint) {
        setRefining(true)
        const refineRes = await axios.post<{ conversation: AiArchitectConversation }>(
          `/ai-architect/conversations/${conversation.id}/refine`,
          {},
          { headers: { Authorization: `Bearer ${token}` } },
        )
        setConversation(refineRes.data.conversation)
      }
      setMessage('')
    } catch (err: any) {
      setError(err?.response?.data?.detail || t('ai.failedSend'))
    } finally {
      setSending(false)
      setRefining(false)
    }
  }

  const generateBlueprint = async () => {
    if (!token || !conversation) return
    setGenerating(true)
    setError('')
    try {
      const res = await axios.post<{ conversation: AiArchitectConversation }>(
        `/ai-architect/conversations/${conversation.id}/generate`,
        {},
        { headers: { Authorization: `Bearer ${token}` } },
      )
      setConversation(res.data.conversation)
    } catch (err: any) {
      setError(err?.response?.data?.detail || t('ai.failedGenerate'))
    } finally {
      setGenerating(false)
    }
  }

  const applyProposal = async (proposal: AiArchitectProposal) => {
    if (!token) return
    try {
      const res = await axios.post<{ proposal: AiArchitectProposal }>(
        `/ai-architect/proposals/${proposal.id}/apply`,
        {},
        { headers: { Authorization: `Bearer ${token}` } },
      )
      setConversation(prev => prev
        ? {
            ...prev,
            proposals: prev.proposals.map(item => item.id === proposal.id ? res.data.proposal : item),
          }
        : prev)
      const historyRes = await axios.get<AiArchitectChangeEvent[]>(
        '/ai-architect/change-events',
        { headers: { Authorization: `Bearer ${token}` } },
      )
      setHistory(historyRes.data)
    } catch (err: any) {
      setError(err?.response?.data?.detail || t('ai.failedApply'))
    }
  }

  const rollbackChange = async (event: AiArchitectChangeEvent) => {
    if (!token) return
    try {
      const res = await axios.post<AiArchitectChangeEvent>(
        `/ai-architect/change-events/${event.id}/rollback`,
        {},
        { headers: { Authorization: `Bearer ${token}` } },
      )
      setHistory(prev => prev.map(item => item.id === event.id ? res.data : item))
    } catch (err: any) {
      setError(err?.response?.data?.detail || t('ai.failedRollback'))
    }
  }

  const summarizeState = (proposal: AiArchitectProposal) => {
    if (proposal.operation === 'create') {
      return proposal.generated_artifacts.map(item => item.name).join(', ')
    }
    if (proposal.proposal_type === 'forms') {
      const beforeFields = Array.isArray(proposal.before_state.schema_structure)
        ? proposal.before_state.schema_structure.length
        : 0
      const afterFields = Array.isArray(proposal.after_state.schema_structure)
        ? proposal.after_state.schema_structure.length
        : 0
      return language === 'ru'
        ? `${beforeFields} полей → ${afterFields} полей`
        : `${beforeFields} fields → ${afterFields} fields`
    }
    return language === 'ru' ? 'Проверьте точное изменение до / после' : 'Review exact before / after change'
  }

  if (loading) {
    return <div className="crm-page-shell">{t('common.loading')}</div>
  }

  return (
    <div className="crm-page-shell" style={{ display: 'flex', flexDirection: 'column', gap: theme.spacing.lg }}>
      <section style={{ background: theme.colors.white, borderRadius: theme.borderRadius.lg, padding: theme.spacing.lg, boxShadow: theme.shadows.sm }}>
        <div style={{ fontSize: '13px', color: theme.colors.gray.textLight }}>{t('nav.aiArchitect')}</div>
        <h1 style={{ margin: `${theme.spacing.xs} 0 ${theme.spacing.sm}` }}>{t('ai.title')}</h1>
        <p style={{ margin: 0, color: theme.colors.gray.text }}>
          {t('ai.subtitle')}
        </p>
      </section>

      {error && (
        <div style={{ color: theme.colors.error, background: theme.colors.status.pending, border: `1px solid ${theme.colors.error}`, borderRadius: theme.borderRadius.md, padding: theme.spacing.md }}>
          {error}
        </div>
      )}

      <section style={{ background: theme.colors.white, borderRadius: theme.borderRadius.lg, padding: theme.spacing.lg, boxShadow: theme.shadows.sm }}>
        <h2 style={{ marginTop: 0 }}>{t('ai.conversation')}</h2>
        <div style={{ display: 'grid', gap: theme.spacing.sm, marginBottom: theme.spacing.md }}>
          {conversation?.messages.length ? conversation.messages.map(item => (
            <div
              key={item.id}
              style={{
                padding: `${theme.spacing.md} ${theme.spacing.lg}`,
                borderRadius: theme.borderRadius.md,
                background: item.sender === 'owner' ? theme.colors.status.assigned : theme.colors.gray.lighter,
              }}
            >
              <strong style={{ display: 'block', marginBottom: theme.spacing.xs }}>{item.sender === 'owner' ? t('ai.you') : 'AI'}</strong>
              <span>{item.content}</span>
            </div>
          )) : (
            <div style={{ color: theme.colors.gray.textLight }}>
              {t('ai.emptyPrompt')}
            </div>
          )}
        </div>

        <form onSubmit={sendMessage} style={{ display: 'flex', gap: theme.spacing.sm, flexWrap: 'wrap' }}>
          <textarea
            value={message}
            onChange={event => setMessage(event.target.value)}
            placeholder={t('ai.placeholder')}
            rows={4}
            style={{
              flex: 1,
              minWidth: '260px',
              borderRadius: theme.borderRadius.md,
              border: `1px solid ${theme.colors.gray.border}`,
              padding: theme.spacing.md,
            }}
          />
          <div style={{ display: 'flex', flexDirection: 'column', gap: theme.spacing.sm }}>
            <button type="submit" disabled={sending || !message.trim()}>
              {sending || refining ? t('ai.thinking') : t('ai.send')}
            </button>
            <button type="button" onClick={generateBlueprint} disabled={generating || !conversation?.messages.length}>
              {generating ? t('ai.generating') : t('ai.generate')}
            </button>
          </div>
        </form>
      </section>

      {conversation?.blueprint && (
        <section style={{ background: theme.colors.white, borderRadius: theme.borderRadius.lg, padding: theme.spacing.lg, boxShadow: theme.shadows.sm }}>
          <h2 style={{ marginTop: 0 }}>{t('ai.blueprint')}</h2>
          <p>{conversation.blueprint.blueprint.business_summary}</p>
          <div style={{ display: 'grid', gap: theme.spacing.md }}>
            <div><strong>{t('ai.departments')}:</strong> {conversation.blueprint.blueprint.departments.join(', ')}</div>
            <div><strong>{t('ai.roles')}:</strong> {conversation.blueprint.blueprint.roles.join(', ')}</div>
            <div><strong>{t('ai.entities')}:</strong> {conversation.blueprint.blueprint.entities.join(', ')}</div>
            <div><strong>{t('ai.assumptions')}:</strong> {conversation.blueprint.blueprint.assumptions.join(', ')}</div>
          </div>
        </section>
      )}

      {conversation?.proposals.length ? (
        <section style={{ display: 'grid', gap: theme.spacing.md }}>
          {conversation.proposals.map(proposal => (
            <article key={proposal.id} style={{ background: theme.colors.white, borderRadius: theme.borderRadius.lg, padding: theme.spacing.lg, boxShadow: theme.shadows.sm }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: theme.spacing.md, flexWrap: 'wrap' }}>
                <div>
                  <h2 style={{ margin: 0 }}>{proposal.title}</h2>
                  <p style={{ marginBottom: theme.spacing.xs }}>{proposal.description}</p>
                  <div style={{ color: theme.colors.gray.textLight }}>{proposal.rationale}</div>
                  <div style={{ display: 'flex', gap: theme.spacing.xs, marginTop: theme.spacing.xs, flexWrap: 'wrap' }}>
                    <span style={{ background: theme.colors.status.assigned, borderRadius: '999px', padding: `${theme.spacing.xs} ${theme.spacing.sm}`, fontSize: '12px' }}>
                      {proposal.operation}
                    </span>
                    <span style={{ background: theme.colors.status.in_process, borderRadius: '999px', padding: `${theme.spacing.xs} ${theme.spacing.sm}`, fontSize: '12px' }}>
                      {proposal.risk_level} {language === 'ru' ? 'риск' : 'risk'}
                    </span>
                    {proposal.target_artifacts.map(target => (
                      <span key={target.id} style={{ background: theme.colors.status.done, borderRadius: '999px', padding: `${theme.spacing.xs} ${theme.spacing.sm}`, fontSize: '12px' }}>
                        {target.type}: {target.name}
                      </span>
                    ))}
                  </div>
                  <div style={{ marginTop: theme.spacing.xs, fontSize: '13px', color: theme.colors.gray.text }}>
                    {summarizeState(proposal)}
                  </div>
                </div>
                <button
                  type="button"
                  disabled={proposal.status === 'applied'}
                  onClick={() => applyProposal(proposal)}
                >
                  {proposal.status === 'applied' ? t('ai.applied') : t('ai.applyProposal')}
                </button>
              </div>
              <div style={{ display: 'flex', gap: theme.spacing.xs, flexWrap: 'wrap', marginTop: theme.spacing.md }}>
                {proposal.generated_artifacts.map(artifact => (
                  <span
                    key={`${artifact.type}-${artifact.name}`}
                    style={{
                      border: `1px solid ${theme.colors.gray.border}`,
                      borderRadius: '999px',
                      padding: `${theme.spacing.xs} ${theme.spacing.sm}`,
                      fontSize: '12px',
                    }}
                  >
                    {artifact.type}: {artifact.name}
                  </span>
                ))}
              </div>
              {proposal.applied_artifacts.length > 0 && (
                <div style={{ marginTop: theme.spacing.md }}>
                  <strong style={{ display: 'block', marginBottom: theme.spacing.sm }}>{t('ai.appliedArtifacts')}</strong>
                  <div style={{ display: 'flex', gap: theme.spacing.xs, flexWrap: 'wrap' }}>
                    {proposal.applied_artifacts.map(artifact => (
                      <span
                        key={`${artifact.type}-${artifact.id}`}
                        style={{
                          background: theme.colors.status.done,
                          border: `1px solid ${theme.colors.success}`,
                          borderRadius: '999px',
                          padding: `${theme.spacing.xs} ${theme.spacing.sm}`,
                          fontSize: '12px',
                        }}
                      >
                        {artifact.type}: {artifact.name}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </article>
          ))}
        </section>
      ) : null}

      <section style={{ background: theme.colors.white, borderRadius: theme.borderRadius.lg, padding: theme.spacing.lg, boxShadow: theme.shadows.sm }}>
        <h2 style={{ marginTop: 0 }}>{t('ai.history')}</h2>
        {history.length ? (
          <div style={{ display: 'grid', gap: theme.spacing.md }}>
            {history.map(event => (
              <article key={event.id} style={{ border: `1px solid ${theme.colors.gray.border}`, borderRadius: theme.borderRadius.md, padding: theme.spacing.md }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: theme.spacing.sm, flexWrap: 'wrap' }}>
                  <div>
                    <strong>{event.operation}</strong>
                    <div style={{ color: theme.colors.gray.textLight, fontSize: '13px' }}>
                      {event.affected_artifacts.map(item => `${item.type}: ${item.name}`).join(', ')}
                    </div>
                    {event.created_at && (
                      <div style={{ color: theme.colors.gray.textLight, fontSize: '12px', marginTop: theme.spacing.xs }}>
                        {new Date(event.created_at).toLocaleString()}
                      </div>
                    )}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: theme.spacing.sm }}>
                    <span style={{ fontSize: '12px', textTransform: 'capitalize' }}>{event.rollback_status.replace('_', ' ')}</span>
                    {event.rollback_status === 'available' && (
                      <button type="button" onClick={() => rollbackChange(event)}>{t('ai.rollback')}</button>
                    )}
                  </div>
                </div>
                {event.rollback_reason && (
                  <div style={{ marginTop: theme.spacing.sm, color: theme.colors.error, fontSize: '13px' }}>
                    {event.rollback_reason}
                  </div>
                )}
              </article>
            ))}
          </div>
        ) : (
          <div style={{ color: theme.colors.gray.textLight }}>{t('ai.noHistory')}</div>
        )}
      </section>
    </div>
  )
}

export default AiArchitectPage
