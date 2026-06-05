import { useState, useEffect, useCallback } from 'react'
import { Search, X, Play, Loader, CheckCircle, AlertCircle, Cpu, Sparkles, ChevronDown, ChevronRight, Wrench, Zap, Clock, ArrowRight, ArrowLeft } from 'lucide-react'
import toast from 'react-hot-toast'
import { toolsApi, skillsApi } from '../services/api'

// ── Type badge ────────────────────────────────────────────────────────────────

function TypeBadge({ type }) {
  const colors = {
    string:  'bg-blue-900/50 text-blue-300 border-blue-700/40',
    integer: 'bg-amber-900/50 text-amber-300 border-amber-700/40',
    number:  'bg-amber-900/50 text-amber-300 border-amber-700/40',
    boolean: 'bg-purple-900/50 text-purple-300 border-purple-700/40',
  }
  return (
    <span className={`px-1.5 py-0.5 rounded text-[10px] font-mono border ${colors[type] || 'bg-gray-800 text-gray-400 border-gray-700'}`}>
      {type || 'any'}
    </span>
  )
}

// ── Execution trace panel ─────────────────────────────────────────────────────

function ExecutionTrace({ trace }) {
  const { params, schema, result, error, ms, toolName } = trace
  const props    = schema?.properties || {}
  const required = new Set(schema?.required || [])

  return (
    <div className="space-y-2 border-t border-gray-800 pt-2 mt-1">
      <div className="flex items-center gap-2">
        {error ? (
          <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-red-900/40 border border-red-700/40 text-[11px] text-red-300 font-medium">
            <AlertCircle className="w-3 h-3" /> Error
          </span>
        ) : (
          <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-900/40 border border-emerald-700/40 text-[11px] text-emerald-300 font-medium">
            <CheckCircle className="w-3 h-3" /> Success
          </span>
        )}
        {ms !== undefined && (
          <span className="flex items-center gap-1 text-[11px] text-gray-500">
            <Clock className="w-3 h-3" /> {ms} ms
          </span>
        )}
        <span className="ml-auto text-[10px] text-gray-600 font-mono">{toolName}</span>
      </div>

      <div className="rounded-lg border border-gray-800 overflow-hidden">
        <div className="flex items-center gap-1.5 px-2.5 py-1 bg-gray-900 border-b border-gray-800">
          <ArrowRight className="w-3 h-3 text-indigo-400" />
          <span className="text-[11px] font-semibold text-indigo-300">Request</span>
        </div>
        <div className="bg-gray-950 px-2.5 py-2 space-y-1.5">
          {Object.keys(props).length === 0 && Object.keys(params).length === 0 ? (
            <p className="text-[11px] text-gray-600 italic">No parameters</p>
          ) : (
            Object.entries(props).map(([k, info]) => (
              <div key={k} className="flex items-center gap-2 text-[11px]">
                <span className="font-mono text-indigo-300 w-24 flex-shrink-0 truncate">{k}</span>
                <TypeBadge type={info.type} />
                {required.has(k) && <span className="text-red-400 text-[9px]">req</span>}
                <span className="font-mono text-emerald-300 flex-1 truncate">
                  {params[k] !== undefined && params[k] !== ''
                    ? JSON.stringify(params[k])
                    : <span className="text-gray-600 italic">—</span>}
                </span>
              </div>
            ))
          )}
          <div className="pt-1 border-t border-gray-800/60">
            <pre className="font-mono text-[10px] text-gray-400 whitespace-pre-wrap">
              {JSON.stringify({ params }, null, 2)}
            </pre>
          </div>
        </div>
      </div>

      <div className="rounded-lg border border-gray-800 overflow-hidden">
        <div className="flex items-center gap-1.5 px-2.5 py-1 bg-gray-900 border-b border-gray-800">
          <ArrowLeft className="w-3 h-3 text-emerald-400" />
          <span className="text-[11px] font-semibold text-emerald-300">Response</span>
          {ms !== undefined && <span className="ml-auto text-[10px] text-gray-600">{ms} ms</span>}
        </div>
        <div className="bg-gray-950 px-2.5 py-2">
          {error
            ? <pre className="font-mono text-[11px] text-red-300 whitespace-pre-wrap">{error}</pre>
            : <pre className="font-mono text-[11px] text-gray-200 whitespace-pre-wrap">
                {typeof result === 'string' ? result : JSON.stringify(result, null, 2)}
              </pre>
          }
        </div>
      </div>
    </div>
  )
}

// ── Inline tool tester ────────────────────────────────────────────────────────

function InlineTester({ tool }) {
  const [params, setParams]   = useState({})
  const [running, setRunning] = useState(false)
  const [trace, setTrace]     = useState(null)
  const [open, setOpen]       = useState(false)

  const schema     = tool.input_schema || {}
  const props      = schema.properties || {}
  const required   = new Set(schema.required || [])
  const paramNames = Object.keys(props)

  const run = async () => {
    setRunning(true); setTrace(null)
    try {
      const res = await skillsApi.executeTool(tool.skill_id, tool.tool_name, params)
      setTrace({ toolName: tool.tool_name, params, schema, result: res.result, ms: res.execution_ms, error: null })
    } catch (e) {
      setTrace({ toolName: tool.tool_name, params, schema, result: null, ms: undefined, error: e.response?.data?.detail || e.message })
    } finally { setRunning(false) }
  }

  if (!tool.has_code) return (
    <span className="text-xs text-gray-600 italic">No implementation</span>
  )

  return (
    <div className="mt-2">
      <button onClick={() => setOpen(o => !o)}
        className="flex items-center gap-1.5 text-xs text-emerald-400 hover:text-emerald-300 transition-colors">
        {open ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
        Test
        {paramNames.length > 0 && <span className="text-[10px] text-gray-600">· {paramNames.length} param{paramNames.length !== 1 ? 's' : ''}</span>}
      </button>
      {open && (
        <div className="mt-2 space-y-2 border-t border-gray-800 pt-2">
          {paramNames.map(name => (
            <div key={name} className="space-y-0.5">
              <div className="flex items-center gap-1.5">
                <span className="text-[11px] font-mono text-indigo-300 font-semibold">{name}</span>
                <TypeBadge type={props[name]?.type} />
                {required.has(name) && <span className="text-[9px] text-red-400">required</span>}
              </div>
              {props[name]?.description && (
                <p className="text-[10px] text-gray-500">{props[name].description}</p>
              )}
              <input
                value={params[name] || ''}
                onChange={e => setParams(p => ({ ...p, [name]: e.target.value }))}
                placeholder={props[name]?.description || `Enter ${name}…`}
                className="input text-xs py-1 font-mono w-full"
              />
            </div>
          ))}
          {paramNames.length === 0 && <p className="text-xs text-gray-600 italic">No parameters</p>}
          <button onClick={run} disabled={running}
            className="btn-primary text-xs py-1 w-full justify-center">
            {running ? <><Loader className="w-3 h-3 animate-spin" /> Running…</> : <><Play className="w-3 h-3" /> Run</>}
          </button>
          {trace && <ExecutionTrace trace={trace} />}
        </div>
      )}
    </div>
  )
}

// ── Tool card ────────────────────────────────────────────────────────────────

function ToolCard({ tool }) {
  const params = Object.keys(tool.input_schema?.properties || {})
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 hover:border-gray-700 transition-colors flex flex-col gap-3">
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-lg flex-shrink-0" style={{ filter: 'drop-shadow(0 0 4px rgba(255,255,255,0.1))' }}>
            {tool.skill_icon}
          </span>
          <div className="min-w-0">
            <p className="text-sm font-mono font-semibold text-white truncate">{tool.tool_name}</p>
            <p className="text-xs text-gray-500 truncate">{tool.skill_name}</p>
          </div>
        </div>
        <div className="flex items-center gap-1 flex-shrink-0">
          {tool.mcp_registered && (
            <span className="flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-medium bg-indigo-900/60 text-indigo-300 border border-indigo-700/40">
              <Cpu className="w-2.5 h-2.5" /> MCP
            </span>
          )}
          {tool.has_code && (
            <span className="flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-medium bg-emerald-900/60 text-emerald-300 border border-emerald-700/40">
              <Zap className="w-2.5 h-2.5" /> Live
            </span>
          )}
        </div>
      </div>

      {/* Description */}
      <p className="text-xs text-gray-400 leading-relaxed line-clamp-2">{tool.description || '—'}</p>

      {/* Params */}
      {params.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {params.map(p => (
            <span key={p} className="px-1.5 py-0.5 bg-gray-800 rounded text-[10px] font-mono text-gray-400">
              {p}: {tool.input_schema.properties[p]?.type || 'any'}
            </span>
          ))}
        </div>
      )}

      {/* Inline tester */}
      <InlineTester tool={tool} />
    </div>
  )
}

// ── AI Tool Generator ────────────────────────────────────────────────────────

function AIToolGenerator({ skills, onGenerated }) {
  const [prompt, setPrompt] = useState('')
  const [skillId, setSkillId] = useState('')
  const [loading, setLoading] = useState(false)
  const [preview, setPreview] = useState(null)

  const generate = async () => {
    if (!prompt.trim()) return
    setLoading(true); setPreview(null)
    try {
      const res = await toolsApi.research(prompt.trim(), skillId || null)
      setPreview(res)
      if (res.added_to_skill) {
        toast.success(`Tool "${res.tool.name}" added to skill!`)
        onGenerated()
      } else {
        toast.success(`Tool generated! Select a skill to save it.`)
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Generation failed')
    } finally { setLoading(false) }
  }

  const saveToSkill = async () => {
    if (!preview || !skillId) return
    setLoading(true)
    try {
      await toolsApi.research(prompt.trim(), skillId)
      toast.success(`Tool added to skill!`)
      setPreview(null); setPrompt('')
      onGenerated()
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Save failed')
    } finally { setLoading(false) }
  }

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 space-y-3">
      <div className="flex items-center gap-2">
        <Sparkles className="w-4 h-4 text-purple-400" />
        <h3 className="text-sm font-semibold text-white">Generate Tool with AI</h3>
      </div>

      <textarea
        value={prompt}
        onChange={e => setPrompt(e.target.value)}
        placeholder="Describe the tool… e.g. 'A tool that converts Markdown to HTML'"
        rows={2}
        className="input w-full text-sm resize-none"
      />

      <div className="flex gap-2">
        <div className="relative flex-1">
          <select value={skillId} onChange={e => setSkillId(e.target.value)}
            className="input w-full text-sm appearance-none pr-8">
            <option value="">— Preview only (don't save) —</option>
            {skills.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
          <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 pointer-events-none" />
        </div>
        <button onClick={generate} disabled={loading || !prompt.trim()}
          className="btn-primary text-sm px-4 flex-shrink-0">
          {loading ? <Loader className="w-4 h-4 animate-spin" /> : <><Sparkles className="w-4 h-4" /> Generate</>}
        </button>
      </div>

      {preview && (
        <div className="border border-purple-800/40 rounded-lg bg-purple-950/20 p-3 space-y-2">
          <p className="text-xs font-semibold text-purple-300">
            Generated: <span className="font-mono">{preview.tool.name}</span>
          </p>
          <p className="text-xs text-gray-400">{preview.tool.description}</p>
          <div className="flex flex-wrap gap-1">
            {Object.keys(preview.tool.input_schema?.properties || {}).map(p => (
              <span key={p} className="px-1.5 py-0.5 bg-gray-800 rounded text-[10px] font-mono text-gray-400">
                {p}: {preview.tool.input_schema.properties[p]?.type || 'any'}
              </span>
            ))}
          </div>
          <pre className="text-[10px] font-mono bg-gray-950 border border-gray-800 rounded p-2 text-gray-300 overflow-x-auto max-h-40 whitespace-pre">
            {preview.tool.code}
          </pre>
          {!preview.added_to_skill && skillId && (
            <button onClick={saveToSkill} disabled={loading}
              className="btn-primary text-xs py-1.5 w-full justify-center">
              <Zap className="w-3 h-3" /> Save to {skills.find(s => s.id === skillId)?.name}
            </button>
          )}
        </div>
      )}
    </div>
  )
}

// ── Main catalog view ────────────────────────────────────────────────────────

export default function ToolsCatalog() {
  const [tools, setTools] = useState([])
  const [skills, setSkills] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [filterMcp, setFilterMcp] = useState(false)
  const [filterLive, setFilterLive] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [t, s] = await Promise.all([
        toolsApi.catalog(),
        skillsApi.list(),
      ])
      setTools(t)
      setSkills(s)
    } catch { toast.error('Failed to load tools catalog') }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  const filtered = tools.filter(t => {
    if (filterMcp && !t.mcp_registered) return false
    if (filterLive && !t.has_code) return false
    if (search) {
      const s = search.toLowerCase()
      return t.tool_name.toLowerCase().includes(s) ||
             t.description.toLowerCase().includes(s) ||
             t.skill_name.toLowerCase().includes(s)
    }
    return true
  })

  return (
    <div className="space-y-6">
      {/* AI Generator */}
      <AIToolGenerator skills={skills} onGenerated={load} />

      {/* Search + filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search tools by name, description, or skill…"
            className="input pl-9 w-full"
          />
          {search && (
            <button onClick={() => setSearch('')} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300">
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
        <div className="flex gap-2">
          <button onClick={() => setFilterMcp(f => !f)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium transition-colors ${filterMcp ? 'bg-indigo-900/60 border-indigo-600 text-indigo-200' : 'border-gray-700 text-gray-400 hover:border-gray-600'}`}>
            <Cpu className="w-3.5 h-3.5" /> MCP Only
          </button>
          <button onClick={() => setFilterLive(f => !f)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium transition-colors ${filterLive ? 'bg-emerald-900/60 border-emerald-600 text-emerald-200' : 'border-gray-700 text-gray-400 hover:border-gray-600'}`}>
            <Zap className="w-3.5 h-3.5" /> Live Only
          </button>
        </div>
      </div>

      {/* Count */}
      {!loading && (
        <p className="text-xs text-gray-600">
          {filtered.length} tool{filtered.length !== 1 ? 's' : ''}
          {(filterMcp || filterLive || search) ? ' matching filters' : ' across all skills'}
          {' '}· {tools.filter(t => t.mcp_registered).length} MCP-registered
        </p>
      )}

      {/* Grid */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 gap-3">
          <Wrench className="w-10 h-10 text-gray-700" />
          <p className="text-gray-500 text-sm">No tools found</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filtered.map(t => <ToolCard key={`${t.skill_id}-${t.tool_name}`} tool={t} />)}
        </div>
      )}
    </div>
  )
}
