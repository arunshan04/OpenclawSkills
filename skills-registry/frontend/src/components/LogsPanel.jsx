import { useState, useEffect, useRef } from 'react'
import { RefreshCw, Circle, Filter } from 'lucide-react'
import { skillsApi } from '../services/api'

const LEVEL_COLORS = {
  INFO:    'text-blue-400',
  WARNING: 'text-amber-400',
  ERROR:   'text-red-400',
  DEBUG:   'text-gray-500',
}

const EVENT_COLORS = {
  TOOL_CALL:        'text-emerald-400',
  TOOL_OK:          'text-emerald-300',
  TOOL_ERROR:       'text-red-400',
  TOOL_TIMEOUT:     'text-orange-400',
  MCP_REGISTER:     'text-indigo-400',
  MCP_SKIP:         'text-amber-400',
  MCP_REGISTER_FAIL:'text-red-400',
  SKILL_CREATE:     'text-cyan-400',
  SKILL_UPDATE:     'text-sky-400',
  SKILL_DELETE:     'text-rose-400',
  STARTUP:          'text-violet-400',
  SERVER_START:     'text-violet-300',
}

function eventType(msg) {
  return Object.keys(EVENT_COLORS).find(k => msg.startsWith(k))
}

function LogRow({ entry }) {
  const ev = eventType(entry.msg)
  const evColor = ev ? EVENT_COLORS[ev] : LEVEL_COLORS[entry.level] || 'text-gray-400'
  const time = entry.ts ? new Date(entry.ts).toLocaleTimeString() : ''
  const levelColor = LEVEL_COLORS[entry.level] || 'text-gray-500'

  return (
    <div className="flex items-start gap-3 px-3 py-1.5 hover:bg-gray-800/50 border-b border-gray-800/40 font-mono text-xs leading-relaxed">
      <span className="text-gray-600 flex-shrink-0 w-20">{time}</span>
      <span className={`flex-shrink-0 w-16 font-semibold ${levelColor}`}>{entry.level}</span>
      <span className={`flex-shrink-0 w-20 text-gray-600`}>{entry.logger}</span>
      <span className={`flex-1 break-all ${evColor}`}>{entry.msg}</span>
    </div>
  )
}

export default function LogsPanel() {
  const [logs, setLogs] = useState([])
  const [total, setTotal] = useState(0)
  const [level, setLevel] = useState('')
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)

  const fetch = async () => {
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

  useEffect(() => { fetch() }, [level])

  useEffect(() => {
    if (!autoRefresh) return
    const id = setInterval(fetch, 3000)
    return () => clearInterval(id)
  }, [autoRefresh, level])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden flex flex-col h-[600px]">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-800 flex-shrink-0">
        <Circle className={`w-2 h-2 flex-shrink-0 ${autoRefresh ? 'text-emerald-400 animate-pulse' : 'text-gray-600'}`} fill="currentColor" />
        <span className="text-sm font-semibold text-white">Activity Log</span>
        <span className="text-xs text-gray-500">{total} entries</span>

        <div className="ml-auto flex items-center gap-2">
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

          <button onClick={fetch} disabled={loading} className="p-1.5 rounded-lg hover:bg-gray-800 transition-colors">
            <RefreshCw className={`w-3.5 h-3.5 text-gray-400 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-x-4 gap-y-1 px-4 py-2 border-b border-gray-800/60 flex-shrink-0">
        {[
          ['TOOL_CALL', 'Tool called'],
          ['TOOL_OK', 'Success'],
          ['TOOL_ERROR', 'Error'],
          ['MCP_REGISTER', 'MCP registered'],
          ['SKILL_CREATE', 'Skill created'],
          ['SKILL_UPDATE', 'Skill updated'],
          ['SKILL_DELETE', 'Skill deleted'],
        ].map(([k, label]) => (
          <span key={k} className={`text-xs font-mono ${EVENT_COLORS[k]}`}>
            ● {label}
          </span>
        ))}
      </div>

      {/* Log rows */}
      <div className="flex-1 overflow-y-auto bg-gray-950">
        {logs.length === 0 ? (
          <div className="flex items-center justify-center h-full text-gray-600 text-sm">
            No log entries yet. Make some tool calls or register a skill.
          </div>
        ) : (
          <>
            {logs.map((entry, i) => <LogRow key={i} entry={entry} />)}
            <div ref={bottomRef} />
          </>
        )}
      </div>
    </div>
  )
}
