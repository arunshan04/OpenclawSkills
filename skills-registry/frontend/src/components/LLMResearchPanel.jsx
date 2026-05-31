import { useState } from 'react'
import { Sparkles, Search, ChevronRight, Loader, AlertCircle, CheckCircle } from 'lucide-react'
import { skillsApi } from '../services/api'
import IconPicker from './IconPicker'

const EXAMPLE_QUERIES = [
  'A skill for monitoring Kubernetes clusters and alerting on anomalies',
  'PDF document parser and content extractor with semantic search',
  'Social media content scheduler and analytics tracker',
  'Database query optimizer and performance analyzer',
  'Email summarization and smart reply generator',
]

export default function LLMResearchPanel({ existingSkills = [], onApply, onClose }) {
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [step, setStep] = useState('input') // input | result | customize

  // Customization state (after LLM result)
  const [customIcon, setCustomIcon] = useState('🔧')
  const [customBgColor, setCustomBgColor] = useState('#6366f1')

  const handleResearch = async () => {
    if (!query.trim()) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const data = await skillsApi.research({
        query,
        category: category || undefined,
        existing_skills: existingSkills.map(s => s.name),
      })
      setResult(data)
      setCustomIcon(data.icon || '🔧')
      setCustomBgColor(data.icon_bg_color || '#6366f1')
      setStep('result')
    } catch (e) {
      const msg = e.response?.data?.detail || e.message || 'Research failed'
      setError(msg.includes('ANTHROPIC_API_KEY') ? 'ANTHROPIC_API_KEY not configured on backend. Set it in .env file.' : msg)
    } finally {
      setLoading(false)
    }
  }

  const handleApply = () => {
    if (!result) return
    onApply({
      name: result.name,
      description: result.description,
      category: result.category,
      icon: customIcon,
      icon_bg_color: customBgColor,
      tags: result.tags || [],
      tools: result.tools || [],
      prompts: result.prompts || [],
      resources: result.resources || [],
      mcp_config: result.mcp_config || {},
      source: 'llm_generated',
      metadata: result.metadata || {},
    })
  }

  return (
    <div className="space-y-4">
      {step === 'input' && (
        <>
          <div className="bg-indigo-950/40 border border-indigo-800/40 rounded-xl p-4">
            <div className="flex items-start gap-3">
              <Sparkles className="w-5 h-5 text-indigo-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-semibold text-indigo-300">AI Skill Research</p>
                <p className="text-xs text-indigo-400/70 mt-0.5">
                  Describe what capability you need — Claude will design a complete skill definition including tools, prompts, and MCP configuration.
                </p>
              </div>
            </div>
          </div>

          <div>
            <label className="section-header">Describe the skill you need</label>
            <textarea
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="e.g. A skill for monitoring cloud costs and generating optimization recommendations..."
              className="input min-h-[100px] resize-none leading-relaxed"
              onKeyDown={e => e.key === 'Enter' && e.ctrlKey && handleResearch()}
            />
            <p className="text-xs text-gray-600 mt-1">Press Ctrl+Enter to research</p>
          </div>

          <div>
            <label className="section-header">Category (optional)</label>
            <select value={category} onChange={e => setCategory(e.target.value)} className="input">
              <option value="">Auto-detect</option>
              {['Research', 'Development', 'Analytics', 'Security', 'Creative', 'Productivity',
                'Communication', 'AI/ML', 'Data', 'Cloud', 'Automation', 'DevOps',
                'Finance', 'Education', 'Healthcare', 'General'].map(c => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>

          <div>
            <p className="section-header">Example queries</p>
            <div className="space-y-1.5">
              {EXAMPLE_QUERIES.map((q, i) => (
                <button
                  key={i}
                  onClick={() => setQuery(q)}
                  className="w-full text-left px-3 py-2 rounded-lg bg-gray-800 hover:bg-gray-750 text-xs text-gray-400 hover:text-gray-200 transition-colors flex items-center justify-between group"
                >
                  <span>{q}</span>
                  <ChevronRight className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                </button>
              ))}
            </div>
          </div>

          {error && (
            <div className="flex items-start gap-2 bg-red-950/40 border border-red-800/40 rounded-lg p-3">
              <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-red-300">{error}</p>
            </div>
          )}

          <button
            onClick={handleResearch}
            disabled={!query.trim() || loading}
            className="btn-primary w-full justify-center py-2.5"
          >
            {loading ? (
              <><Loader className="w-4 h-4 animate-spin" /> Researching with Claude...</>
            ) : (
              <><Sparkles className="w-4 h-4" /> Research Skill</>
            )}
          </button>
        </>
      )}

      {step === 'result' && result && (
        <>
          {/* Result header */}
          <div className="flex items-center gap-2 bg-emerald-950/30 border border-emerald-800/30 rounded-lg p-3">
            <CheckCircle className="w-4 h-4 text-emerald-400" />
            <p className="text-sm text-emerald-300 font-medium">Skill designed by Claude</p>
          </div>

          {/* Preview card */}
          <div className="bg-gray-950 border border-gray-800 rounded-xl p-4">
            <div className="flex items-start gap-3 mb-3">
              <div
                className="w-12 h-12 rounded-xl flex items-center justify-center text-2xl shadow-md flex-shrink-0"
                style={{ backgroundColor: customBgColor }}
              >
                {customIcon}
              </div>
              <div>
                <h3 className="font-semibold text-white">{result.name}</h3>
                <p className="text-xs text-gray-500">{result.category}</p>
              </div>
            </div>
            <p className="text-xs text-gray-400 leading-relaxed mb-3">{result.description}</p>
            <div className="flex flex-wrap gap-1 mb-3">
              {(result.tags || []).map(tag => <span key={tag} className="tag">{tag}</span>)}
            </div>
            <div className="flex items-center gap-4 text-xs text-gray-500 pt-2 border-t border-gray-800">
              <span>🔧 {(result.tools || []).length} tools</span>
              <span>⚡ {(result.prompts || []).length} prompts</span>
              {result.mcp_config?.transport && <span>🔌 {result.mcp_config.transport}</span>}
            </div>
          </div>

          {/* Rationale */}
          {result.rationale && (
            <div className="bg-gray-950 border border-gray-800 rounded-lg p-3">
              <p className="text-xs font-semibold text-gray-500 mb-1">Claude's Rationale</p>
              <p className="text-xs text-gray-400 leading-relaxed">{result.rationale}</p>
            </div>
          )}

          {/* Icon customization */}
          <div className="bg-gray-950 border border-gray-800 rounded-xl p-4">
            <p className="section-header">Customize Icon</p>
            <IconPicker
              icon={customIcon}
              bgColor={customBgColor}
              onIconChange={setCustomIcon}
              onBgColorChange={setCustomBgColor}
            />
          </div>

          <div className="flex gap-2">
            <button onClick={() => { setStep('input'); setResult(null) }} className="btn-secondary flex-1 justify-center">
              ← Research Again
            </button>
            <button onClick={handleApply} className="btn-primary flex-1 justify-center">
              <CheckCircle className="w-4 h-4" /> Use This Skill
            </button>
          </div>
        </>
      )}
    </div>
  )
}
