import { useState } from 'react'
import { X, Wrench, Zap, Database, Copy, Trash2, Edit, CheckCircle, Tag, User, Clock, Server, Code } from 'lucide-react'
import { skillToYaml } from '../services/yaml'
import ToolTester from './ToolTester'

function JsonBlock({ data, isYaml = false }) {
  const [copied, setCopied] = useState(false)
  const text = isYaml ? data : JSON.stringify(data, null, 2)
  const copy = () => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  return (
    <div className="relative group">
      <pre className="text-xs font-mono bg-gray-950 border border-gray-800 rounded-lg p-3 overflow-x-auto text-gray-300 max-h-96 leading-relaxed">
        {text}
      </pre>
      <button
        onClick={copy}
        className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 p-1.5 rounded-md bg-gray-800 hover:bg-gray-700 transition-all"
        title="Copy to clipboard"
      >
        {copied ? <CheckCircle className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5 text-gray-400" />}
      </button>
    </div>
  )
}

function TabButton({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
        active ? 'bg-indigo-600 text-white' : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800'
      }`}
    >
      {children}
    </button>
  )
}

export default function SkillDetailModal({ skill, onClose, onDelete, onEdit }) {
  const [tab, setTab] = useState('overview')
  const [deleting, setDeleting] = useState(false)

  const handleDelete = async () => {
    if (!deleting) { setDeleting(true); return }
    try {
      await onDelete(skill.id)
      onClose()
    } catch {
      setDeleting(false)
    }
  }

  const mcpConfig = typeof skill.mcp_config === 'string' ? JSON.parse(skill.mcp_config) : skill.mcp_config
  const tools = typeof skill.tools === 'string' ? JSON.parse(skill.tools) : skill.tools || []
  const prompts = typeof skill.prompts === 'string' ? JSON.parse(skill.prompts) : skill.prompts || []
  const resources = typeof skill.resources === 'string' ? JSON.parse(skill.resources) : skill.resources || []
  const tags = typeof skill.tags === 'string' ? JSON.parse(skill.tags) : skill.tags || []
  const metadata = typeof skill.metadata === 'string' ? JSON.parse(skill.metadata) : skill.metadata || {}

  return (
    <div className="modal-overlay animate-fade-in" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal-content max-w-2xl animate-slide-up">
        {/* Header */}
        <div className="flex items-start gap-4 p-6 border-b border-gray-800 sticky top-0 bg-gray-900 z-10 rounded-t-2xl">
          <div
            className="w-14 h-14 rounded-2xl flex items-center justify-center text-3xl shadow-lg flex-shrink-0"
            style={{ backgroundColor: skill.icon_bg_color || '#6366f1' }}
          >
            {skill.icon || '🔧'}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h2 className="text-lg font-bold text-white">{skill.name}</h2>
              <span className={`badge ${skill.status === 'active' ? 'status-active' : 'status-inactive'}`}>
                {skill.status}
              </span>
              {skill.source === 'llm_generated' && (
                <span className="badge source-llm">✨ AI Generated</span>
              )}
            </div>
            <p className="text-sm text-gray-400 mt-0.5">{skill.category} · v{skill.version}</p>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={() => onEdit(skill)} className="btn-secondary text-xs py-1.5">
              <Edit className="w-3.5 h-3.5" /> Edit
            </button>
            <button onClick={onClose} className="p-2 rounded-lg hover:bg-gray-800 transition-colors">
              <X className="w-4 h-4 text-gray-400" />
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex items-center gap-1 px-6 pt-4 pb-2 flex-wrap">
          {['overview', 'tools', 'prompts', 'mcp', 'yaml', 'metadata'].map(t => (
            <TabButton key={t} active={tab === t} onClick={() => setTab(t)}>
              {t === 'yaml' ? '📄 YAML' : t.charAt(0).toUpperCase() + t.slice(1)}
              {t === 'tools' && tools.length > 0 && <span className="ml-1 text-gray-500">({tools.length})</span>}
              {t === 'prompts' && prompts.length > 0 && <span className="ml-1 text-gray-500">({prompts.length})</span>}
            </TabButton>
          ))}
        </div>

        {/* Content */}
        <div className="px-6 pb-6 pt-2">
          {tab === 'overview' && (
            <div className="space-y-4">
              <div>
                <p className="section-header">Description</p>
                <p className="text-sm text-gray-300 leading-relaxed">{skill.description || 'No description.'}</p>
              </div>

              {tags.length > 0 && (
                <div>
                  <p className="section-header flex items-center gap-1"><Tag className="w-3 h-3" /> Tags</p>
                  <div className="flex flex-wrap gap-1.5">
                    {tags.map(tag => <span key={tag} className="tag">{tag}</span>)}
                  </div>
                </div>
              )}

              <div className="grid grid-cols-2 gap-3">
                <div className="bg-gray-950 rounded-lg p-3 border border-gray-800">
                  <p className="text-xs text-gray-500 mb-1 flex items-center gap-1"><User className="w-3 h-3" /> Author</p>
                  <p className="text-sm text-gray-200 font-medium">{skill.author || 'Unknown'}</p>
                </div>
                <div className="bg-gray-950 rounded-lg p-3 border border-gray-800">
                  <p className="text-xs text-gray-500 mb-1">Version</p>
                  <p className="text-sm text-gray-200 font-mono font-medium">v{skill.version}</p>
                </div>
                <div className="bg-gray-950 rounded-lg p-3 border border-gray-800">
                  <p className="text-xs text-gray-500 mb-1 flex items-center gap-1"><Clock className="w-3 h-3" /> Created</p>
                  <p className="text-sm text-gray-200">{new Date(skill.created_at).toLocaleDateString()}</p>
                </div>
                <div className="bg-gray-950 rounded-lg p-3 border border-gray-800">
                  <p className="text-xs text-gray-500 mb-1">Capabilities</p>
                  <p className="text-sm text-gray-200">
                    {tools.length} tools, {prompts.length} prompts
                    {resources.length > 0 && `, ${resources.length} resources`}
                  </p>
                </div>
              </div>
            </div>
          )}

          {tab === 'tools' && (
            <div className="space-y-3">
              {tools.length === 0 ? (
                <p className="text-sm text-gray-500 text-center py-8">No tools defined for this skill.</p>
              ) : tools.map((tool, i) => (
                <div key={i} className="bg-gray-950 border border-gray-800 rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-1">
                    <Wrench className="w-4 h-4 text-indigo-400 flex-shrink-0" />
                    <code className="text-sm font-mono text-indigo-300 font-medium">{tool.name}</code>
                    {tool.code
                      ? <span className="ml-auto badge bg-emerald-900/40 text-emerald-400 border border-emerald-800/50"><Code className="w-3 h-3 mr-1" />implemented</span>
                      : <span className="ml-auto badge bg-gray-800 text-gray-500 border border-gray-700">no code</span>
                    }
                  </div>
                  <p className="text-xs text-gray-400 mb-3">{tool.description}</p>

                  {tool.code && (
                    <div className="mb-3">
                      <p className="text-xs text-gray-600 mb-1 flex items-center gap-1"><Code className="w-3 h-3" /> Implementation</p>
                      <JsonBlock data={tool.code} isYaml />
                    </div>
                  )}

                  {tool.input_schema && (
                    <div className="mb-2">
                      <p className="text-xs text-gray-600 mb-1">Input Schema</p>
                      <JsonBlock data={tool.input_schema} />
                    </div>
                  )}

                  <ToolTester skill={skill} tool={tool} />
                </div>
              ))}
            </div>
          )}

          {tab === 'prompts' && (
            <div className="space-y-3">
              {prompts.length === 0 ? (
                <p className="text-sm text-gray-500 text-center py-8">No prompts defined for this skill.</p>
              ) : prompts.map((prompt, i) => (
                <div key={i} className="bg-gray-950 border border-gray-800 rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Zap className="w-4 h-4 text-amber-400 flex-shrink-0" />
                    <code className="text-sm font-mono text-amber-300 font-medium">{prompt.name}</code>
                  </div>
                  <p className="text-xs text-gray-400 mb-2">{prompt.description}</p>
                  {prompt.template && (
                    <pre className="text-xs font-mono bg-gray-900 border border-gray-700 rounded p-3 text-gray-300 whitespace-pre-wrap">
                      {prompt.template}
                    </pre>
                  )}
                </div>
              ))}
            </div>
          )}

          {tab === 'mcp' && (
            <div className="space-y-4">
              <div>
                <p className="section-header flex items-center gap-1"><Server className="w-3 h-3" /> MCP Configuration</p>
                <JsonBlock data={mcpConfig || {}} />
              </div>
              <div>
                <p className="section-header">Skill ID</p>
                <code className="text-xs font-mono text-gray-300 bg-gray-950 border border-gray-800 rounded px-2 py-1">
                  {skill.id}
                </code>
              </div>
              <div className="bg-indigo-950/30 border border-indigo-800/30 rounded-lg p-4">
                <p className="text-xs font-semibold text-indigo-400 mb-2">MCP Server Endpoint</p>
                <code className="text-xs font-mono text-indigo-300">
                  http://localhost:8000/mcp
                </code>
                <p className="text-xs text-indigo-400/60 mt-1">
                  Connect your MCP client to this Skills Registry endpoint to access all registered skills.
                </p>
              </div>
            </div>
          )}

          {tab === 'yaml' && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <p className="section-header">SKILL.md — YAML Definition</p>
                <span className="text-xs text-gray-600">Full skill spec in YAML format</span>
              </div>
              <JsonBlock data={skillToYaml(skill)} isYaml />
              <div className="bg-indigo-950/30 border border-indigo-800/30 rounded-lg p-3">
                <p className="text-xs text-indigo-400/80">
                  Save this as <code className="font-mono">SKILL.md</code> in any Claude Code workspace to register this skill.
                </p>
              </div>
            </div>
          )}

          {tab === 'metadata' && (
            <div className="space-y-3">
              <div>
                <p className="section-header">Skill Metadata</p>
                <JsonBlock data={metadata} />
              </div>
              {resources.length > 0 && (
                <div>
                  <p className="section-header flex items-center gap-1"><Database className="w-3 h-3" /> Resources</p>
                  {resources.map((r, i) => (
                    <div key={i} className="bg-gray-950 border border-gray-800 rounded-lg p-3 mb-2">
                      <code className="text-xs font-mono text-cyan-300">{r.uri}</code>
                      <p className="text-xs text-gray-500 mt-1">{r.name} {r.description && `— ${r.description}`}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 pb-6">
          <button onClick={handleDelete} className="btn-danger">
            <Trash2 className="w-3.5 h-3.5" />
            {deleting ? 'Click again to confirm delete' : 'Delete Skill'}
          </button>
          <button onClick={onClose} className="btn-secondary">Close</button>
        </div>
      </div>
    </div>
  )
}
