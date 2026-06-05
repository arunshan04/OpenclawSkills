import { useState } from 'react'
import { Play, Loader, CheckCircle, AlertCircle, ChevronDown, ChevronRight, Clock, ArrowRight, ArrowLeft, Hash } from 'lucide-react'
import { skillsApi } from '../services/api'

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

function ParamRow({ name, info, required, value, onChange }) {
  return (
    <div className="grid grid-cols-[1fr_2fr] gap-2 items-start">
      <div className="flex flex-col gap-0.5 pt-1.5">
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-mono text-indigo-300 font-semibold">{name}</span>
          {required && <span className="text-[9px] text-red-400 font-medium">required</span>}
        </div>
        <TypeBadge type={info?.type} />
        {info?.description && (
          <span className="text-[10px] text-gray-500 leading-tight mt-0.5">{info.description}</span>
        )}
      </div>
      <input
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={info?.description || `Enter ${name}…`}
        className="input text-xs py-1.5 font-mono"
      />
    </div>
  )
}

function ExecutionTrace({ trace }) {
  const { params, schema, result, error, ms, tool } = trace
  const props   = schema?.properties || {}
  const required = new Set(schema?.required || [])

  return (
    <div className="space-y-3 border-t border-gray-800 pt-3 mt-1">
      {/* Timing bar */}
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
        <span className="text-[11px] text-gray-600 font-mono ml-auto">{tool}</span>
      </div>

      {/* Request */}
      <div className="rounded-lg border border-gray-800 overflow-hidden">
        <div className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-900 border-b border-gray-800">
          <ArrowRight className="w-3 h-3 text-indigo-400" />
          <span className="text-[11px] font-semibold text-indigo-300">Request</span>
        </div>
        <div className="bg-gray-950 px-3 py-2.5 space-y-1.5">
          {Object.keys(props).length === 0 && Object.keys(params).length === 0 ? (
            <p className="text-[11px] text-gray-600 italic">No parameters</p>
          ) : (
            Object.entries(props).map(([k, info]) => (
              <div key={k} className="flex items-start gap-2 text-[11px]">
                <span className="font-mono text-indigo-300 w-28 flex-shrink-0 truncate">{k}</span>
                <TypeBadge type={info.type} />
                {required.has(k) && <span className="text-red-400 text-[9px] mt-0.5">req</span>}
                <span className="font-mono text-emerald-300 flex-1 truncate">
                  {params[k] !== undefined && params[k] !== '' ? JSON.stringify(params[k]) : <span className="text-gray-600 italic">—</span>}
                </span>
              </div>
            ))
          )}
          <div className="pt-1 border-t border-gray-800/60">
            <p className="text-[10px] text-gray-600 mb-1">Raw JSON body</p>
            <pre className="font-mono text-[10px] text-gray-300 whitespace-pre-wrap">
              {JSON.stringify({ params }, null, 2)}
            </pre>
          </div>
        </div>
      </div>

      {/* Response */}
      <div className="rounded-lg border border-gray-800 overflow-hidden">
        <div className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-900 border-b border-gray-800">
          <ArrowLeft className="w-3 h-3 text-emerald-400" />
          <span className="text-[11px] font-semibold text-emerald-300">Response</span>
          {ms !== undefined && (
            <span className="ml-auto text-[10px] text-gray-600">{ms} ms</span>
          )}
        </div>
        <div className="bg-gray-950 px-3 py-2.5">
          {error ? (
            <pre className="font-mono text-[11px] text-red-300 whitespace-pre-wrap leading-relaxed">{error}</pre>
          ) : (
            <pre className="font-mono text-[11px] text-gray-200 whitespace-pre-wrap leading-relaxed">
              {typeof result === 'string' ? result : JSON.stringify(result, null, 2)}
            </pre>
          )}
        </div>
      </div>
    </div>
  )
}

export default function ToolTester({ skill, tool }) {
  const [open, setOpen]     = useState(false)
  const [params, setParams] = useState({})
  const [running, setRunning] = useState(false)
  const [trace, setTrace]   = useState(null)

  const hasCode   = !!(tool.code && tool.code.trim())
  const schema    = tool.input_schema || {}
  const props     = schema.properties || {}
  const required  = new Set(schema.required || [])
  const paramNames = Object.keys(props)

  const run = async () => {
    setRunning(true)
    setTrace(null)
    try {
      const res = await skillsApi.executeTool(skill.id, tool.name, params)
      setTrace({
        tool:   tool.name,
        params,
        schema,
        result: res.result,
        ms:     res.execution_ms,
        error:  null,
      })
    } catch (e) {
      setTrace({
        tool:   tool.name,
        params,
        schema,
        result: null,
        ms:     undefined,
        error:  e.response?.data?.detail || e.message || 'Execution failed',
      })
    } finally {
      setRunning(false)
    }
  }

  if (!hasCode) return null

  return (
    <div className="mt-2 border border-gray-800 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center gap-2 px-3 py-2 bg-gray-900 hover:bg-gray-800 transition-colors text-left"
      >
        {open
          ? <ChevronDown  className="w-3.5 h-3.5 text-emerald-400" />
          : <ChevronRight className="w-3.5 h-3.5 text-emerald-400" />}
        <span className="text-xs font-medium text-emerald-400">Test Tool</span>
        {paramNames.length > 0 && (
          <span className="text-[10px] text-gray-600 ml-1 flex items-center gap-0.5">
            <Hash className="w-2.5 h-2.5" />{paramNames.length} param{paramNames.length !== 1 ? 's' : ''}
          </span>
        )}
      </button>

      {open && (
        <div className="p-3 space-y-3 bg-gray-950 border-t border-gray-800">
          {/* Input params */}
          {paramNames.length > 0 ? (
            <div className="space-y-2.5">
              <p className="text-[11px] text-gray-500 uppercase tracking-wide font-medium">Input Parameters</p>
              {paramNames.map(name => (
                <ParamRow
                  key={name}
                  name={name}
                  info={props[name]}
                  required={required.has(name)}
                  value={params[name] || ''}
                  onChange={v => setParams(p => ({ ...p, [name]: v }))}
                />
              ))}
            </div>
          ) : (
            <p className="text-xs text-gray-600 italic">No input parameters</p>
          )}

          <button
            onClick={run}
            disabled={running}
            className="btn-primary text-xs py-1.5 w-full justify-center"
          >
            {running
              ? <><Loader className="w-3 h-3 animate-spin" /> Running…</>
              : <><Play className="w-3 h-3" /> Run</>}
          </button>

          {trace && <ExecutionTrace trace={trace} />}
        </div>
      )}
    </div>
  )
}
