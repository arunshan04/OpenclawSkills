import { useState } from 'react'
import { Play, Loader, CheckCircle, AlertCircle, ChevronDown, ChevronRight } from 'lucide-react'
import { skillsApi } from '../services/api'

function ParamInput({ name, value, onChange }) {
  return (
    <div className="flex items-center gap-2">
      <label className="text-xs font-mono text-indigo-300 w-28 flex-shrink-0">{name}</label>
      <input
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={`value for ${name}`}
        className="input text-xs py-1.5 font-mono flex-1"
      />
    </div>
  )
}

export default function ToolTester({ skill, tool }) {
  const [open, setOpen] = useState(false)
  const [params, setParams] = useState({})
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const hasCode = !!(tool.code && tool.code.trim())
  const schemaProps = tool.input_schema?.properties || {}
  const paramNames = Object.keys(schemaProps)

  const run = async () => {
    setRunning(true)
    setResult(null)
    setError(null)
    try {
      const res = await skillsApi.executeTool(skill.id, tool.name, params)
      setResult(res.result)
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Execution failed')
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
        {open ? <ChevronDown className="w-3.5 h-3.5 text-emerald-400" /> : <ChevronRight className="w-3.5 h-3.5 text-emerald-400" />}
        <span className="text-xs font-medium text-emerald-400">Test Tool</span>
      </button>

      {open && (
        <div className="p-3 space-y-3 bg-gray-950 border-t border-gray-800">
          {paramNames.length > 0 ? (
            <div className="space-y-2">
              <p className="text-xs text-gray-500">Input Parameters</p>
              {paramNames.map(name => (
                <ParamInput
                  key={name}
                  name={name}
                  value={params[name] || ''}
                  onChange={v => setParams(p => ({ ...p, [name]: v }))}
                />
              ))}
            </div>
          ) : (
            <p className="text-xs text-gray-600 italic">No input parameters defined</p>
          )}

          <button
            onClick={run}
            disabled={running}
            className="btn-primary text-xs py-1.5 w-full justify-center"
          >
            {running ? <><Loader className="w-3 h-3 animate-spin" /> Running...</> : <><Play className="w-3 h-3" /> Run</>}
          </button>

          {result !== null && (
            <div className="space-y-1">
              <div className="flex items-center gap-1">
                <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
                <span className="text-xs font-medium text-emerald-400">Result</span>
              </div>
              <pre className="text-xs font-mono bg-gray-900 border border-gray-800 rounded p-2 text-gray-200 overflow-x-auto whitespace-pre-wrap">
                {typeof result === 'string' ? result : JSON.stringify(result, null, 2)}
              </pre>
            </div>
          )}

          {error && (
            <div className="space-y-1">
              <div className="flex items-center gap-1">
                <AlertCircle className="w-3.5 h-3.5 text-red-400" />
                <span className="text-xs font-medium text-red-400">Error</span>
              </div>
              <pre className="text-xs font-mono bg-red-950/30 border border-red-800/40 rounded p-2 text-red-300 overflow-x-auto whitespace-pre-wrap">
                {error}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
