import { useState, useEffect, useRef } from 'react'
import { RefreshCw, Circle, Filter, ChevronDown, ChevronRight, ArrowRight, ArrowLeft, Clock, CheckCircle, AlertCircle } from 'lucide-react'
import { skillsApi } from '../services/api'

const LEVEL_COLORS = {
  INFO:    'text-blue-400',
  WARNING: 'text-amber-400',
  ERROR:   'text-red-400',
  DEBUG:   'text-gray-500',
}

const EVENT_META = {
  TOOL_CALL:         { color: 'text-emerald-400',  label: 'Tool called' },
  TOOL_OK:           { color: 'text-emerald-300',  label: 'Success' },
  TOOL_ERROR:        { color: 'text-red-400',       label: 'Error' },
  TOOL_TIMEOUT:      { color: 'text-orange-400',    label: 'Timeout' },
  MCP_REGISTER:      { color: 'text-indigo-400',    label: 'MCP registered' },
  MCP_SKIP:          { color: 'text-amber-400',     label: 'MCP skip' },
  MCP_REGISTER_FAIL: { color: 'text-red-400',       label: 'MCP fail' },
  SKILL_CREATE:      { color: 'text-cyan-400',      label: 'Skill created' },
  SKILL_UPDATE:      { color: 'text-sky-400',       label: 'Skill updated' },
  SKILL_DELETE:      { color: 'text-rose-400',      label: 'Skill deleted' },
  STARTUP:           { color: 'text-violet-400',    label: 'Startup' },
  SERVER_START:      { color: 'text-violet-300',    label: 'Server start' },
}

function eventKey(msg) {
  return Object.keys(EVENT_META).find(k => msg.startsWith(k))
}

// ── Verbose tool trace (inline expand) ───────────────────────────────────────

function ToolTrace({ entry }) {
  const params = entry.params || {}
  const paramKeys = Object.keys(params)
  const isOk    = entry.event === 'TOOL_OK'
  const isErr   = entry.event === 'TOOL_ERROR' || entry.event === 'TOOL_TIMEOUT'

  return (
    <div className="mx-3 mb-2 mt-0.5 rounded-lg border border-gray-800 overflow-hidden text-[11px] font-mono">
      {/* Request */}
      <div className="border-b border-gray-800">
        <div className="flex items-center gap-1.5 px-2.5 py-1 bg-gray-900">
          <ArrowRight className="w-3 h-3 text-indigo-400 flex-shrink-0" />
          <span className="font-semibold text-indigo-300">Request</span>
          <span className="text-gray-600 ml-1">{entry.tool}</span>
          {entry.skill_name && <span className="ml-auto text-gray-600">[{entry.skill_name}]</span>}
        </div>
        <div className="bg-gray-950 px-3 py-2">
          {paramKeys.length === 0 ? (
            <span className="text-gray-600 italic">no parameters</span>
          ) : (
            <div className="space-y-1">
              {paramKeys.map(k => (
                <div key={k} className="flex gap-2">
                  <span className="text-indigo-300 w-28 flex-shrink-0 truncate">{k}</span>
                  <span className="text-emerald-300 break-all">{JSON.stringify(params[k])}</span>
                </div>
              ))}
              <div className="pt-1.5 border-t border-gray-800/50 text-gray-500">
                {JSON.stringify({ params })}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Response — only on TOOL_OK / TOOL_ERROR */}
      {(isOk || isErr) && (
        <div>
          <div className="flex items-center gap-1.5 px-2.5 py-1 bg-gray-900">
            <ArrowLeft className={`w-3 h-3 flex-shrink-0 ${isErr ? 'text-red-400' : 'text-emerald-400'}`} />
            <span className={`font-semibold ${isErr ? 'text-red-300' : 'text-emerald-300'}`}>
              Response
            </span>
            {entry.execution_ms !== undefined && (
              <span className="flex items-center gap-1 ml-2 text-gray-500">
                <Clock className="w-2.5 h-2.5" /> {entry.execution_ms} ms
              </span>
            )}
            {isOk  && <CheckCircle className="w-3 h-3 text-emerald-400 ml-auto" />}
            {isErr && <AlertCircle className="w-3 h-3 text-red-400 ml-auto" />}
          </div>
          <div className="bg-gray-950 px-3 py-2">
            {isErr ? (
              <span className="text-red-300 break-all">{entry.error || 'Unknown error'}</span>
            ) : (
              <span className="text-gray-200 break-all whitespace-pre-wrap">
                {typeof entry.result === 'string' ? entry.result : JSON.stringify(entry.result)}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Log row ───────────────────────────────────────────────────────────────────

function LogRow({ entry }) {
  const [expanded, setExpanded] = useState(false)
  const ev = eventKey(entry.msg)
  const meta = ev ? EVENT_META[ev] : null
  const evColor = meta?.color || LEVEL_COLORS[entry.level] || 'text-gray-400'
  const time = entry.ts ? new Date(entry.ts).toLocaleTimeString() : ''
  const levelColor = LEVEL_COLORS[entry.level] || 'text-gray-500'

  const isToolEvent = entry.event && (
    entry.event === 'TOOL_CALL' || entry.event === 'TOOL_OK' || entry.event === 'TOOL_ERROR' || entry.event === 'TOOL_TIMEOUT'
  )
  const hasTrace = isToolEvent && (entry.params !== undefined || entry.result !== undefined || entry.error !== undefined)

  return (
    <div className={`border-b border-gray-800/40 ${hasTrace ? 'cursor-pointer select-none' : ''}`}>
      <div
        className="flex items-start gap-3 px-3 py-1.5 hover:bg-gray-800/40 font-mono text-xs leading-relaxed"
        onClick={() => hasTrace && setExpanded(e => !e)}
      >
        <span className="text-gray-600 flex-shrink-0 w-20">{time}</span>
        <span className={`flex-shrink-0 w-14 font-semibold ${levelColor}`}>{entry.level}</span>
        {hasTrace && (
          <span className="flex-shrink-0 text-gray-600 mt-px">
            {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
          </span>
        )}
        <span className={`flex-1 break-all ${evColor}`}>{entry.msg}</span>
        {entry.execution_ms !== undefined && (
          <span className="flex-shrink-0 text-gray-600 ml-2">{entry.execution_ms}ms</span>
        )}
      </div>
      {expanded && hasTrace && <ToolTrace entry={entry} />}
    </div>
  )
}

// ── Main panel ────────────────────────────────────────────────────────────────

export default function LogsPanel() {
  const [logs, setLogs]           = useState([])
  const [total, setTotal]         = useState(0)
  const [level, setLevel]         = useState('')
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [loading, setLoading]     = useState(false)
  const [verbose, setVerbose]     = useState(true)
  const bottomRef = useRef(null)

  const fetchLogs = async () => {
    setLoading(true)
    try {
      const data = await skillsApi.logs(200, level || null)
      setLogs(data.logs)
      setTotal(data.total)
    } catch {
      // backend might be down
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchLogs() }, [level])

  useEffect(() => {
    if (!autoRefresh) return
    const id = setInterval(fetchLogs, 3000)
    return () => clearInterval(id)
  }, [autoRefresh, level])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  // In verbose mode auto-expand all tool entries — pass verbose as prop
  const displayLogs = verbose
    ? logs
    : logs.filter(e => !e.event?.startsWith('TOOL_OK'))  // collapse OK dupes in non-verbose

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden flex flex-col h-[600px]">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-800 flex-shrink-0">
        <Circle className={`w-2 h-2 flex-shrink-0 ${autoRefresh ? 'text-emerald-400 animate-pulse' : 'text-gray-600'}`} fill="currentColor" />
        <span className="text-sm font-semibold text-white">Activity Log</span>
        <span className="text-xs text-gray-500">{total} entries</span>

        <div className="ml-auto flex items-center gap-2">
          {/* Verbose toggle */}
          <button
            onClick={() => setVerbose(v => !v)}
            className={`text-xs px-2 py-1 rounded-lg border transition-colors ${
              verbose
                ? 'bg-indigo-900/40 border-indigo-600/60 text-indigo-300'
                : 'bg-gray-800 border-gray-700 text-gray-400 hover:text-gray-300'
            }`}
            title="Toggle verbose mode — click tool rows to expand params & result"
          >
            Verbose
          </button>

          <Filter className="w-3.5 h-3.5 text-gray-500" />
          <select
            value={level}
            onChange={e => setLevel(e.target.value)}
            className="bg-gray-800 border border-gray-700 text-xs text-gray-300 rounded-lg px-2 py-1 focus:outline-none"
          >
            <option value="">All levels</option>
            <option value="INFO">INFO</option>
            <option value="WARNING">WARNING</option>
            <option value="ERROR">ERROR</option>
          </select>

          <button
            onClick={() => setAutoRefresh(a => !a)}
            className={`text-xs px-2 py-1 rounded-lg border transition-colors ${
              autoRefresh
                ? 'bg-emerald-900/30 border-emerald-700/50 text-emerald-400'
                : 'bg-gray-800 border-gray-700 text-gray-400'
            }`}
          >
            {autoRefresh ? 'Live' : 'Paused'}
          </button>

          <button onClick={fetchLogs} disabled={loading} className="p-1.5 rounded-lg hover:bg-gray-800 transition-colors">
            <RefreshCw className={`w-3.5 h-3.5 text-gray-400 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-x-4 gap-y-1 px-4 py-2 border-b border-gray-800/60 flex-shrink-0 text-xs">
        {[
          ['TOOL_CALL', 'Tool called'],
          ['TOOL_OK',   'Success'],
          ['TOOL_ERROR','Error'],
          ['MCP_REGISTER', 'MCP registered'],
          ['SKILL_CREATE', 'Skill created'],
          ['SKILL_UPDATE', 'Skill updated'],
          ['SKILL_DELETE', 'Skill deleted'],
        ].map(([k, label]) => (
          <span key={k} className={`font-mono ${EVENT_META[k]?.color || 'text-gray-500'}`}>
            ● {label}
          </span>
        ))}
        {verbose && (
          <span className="text-gray-600 ml-auto italic">click tool rows to expand</span>
        )}
      </div>

      {/* Log rows */}
      <div className="flex-1 overflow-y-auto bg-gray-950">
        {displayLogs.length === 0 ? (
          <div className="flex items-center justify-center h-full text-gray-600 text-sm">
            No log entries yet. Make some tool calls or register a skill.
          </div>
        ) : (
          <>
            {displayLogs.map((entry, i) => (
              <LogRow key={i} entry={entry} verbose={verbose} />
            ))}
            <div ref={bottomRef} />
          </>
        )}
      </div>
    </div>
  )
}
