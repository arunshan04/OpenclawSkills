import { useState } from 'react'
import { X, Plus, Trash2, Sparkles, Wrench, Zap, Copy, CheckCircle, ChevronDown } from 'lucide-react'
import toast from 'react-hot-toast'
import IconPicker from './IconPicker'
import LLMResearchPanel from './LLMResearchPanel'
import { skillsApi } from '../services/api'
import { skillToYaml } from '../services/yaml'

const CATEGORIES = [
  'Research', 'Development', 'Analytics', 'Security', 'Creative',
  'Productivity', 'Communication', 'AI/ML', 'Data', 'Cloud',
  'Automation', 'DevOps', 'Finance', 'Education', 'Healthcare', 'General'
]

function TagInput({ tags, onChange }) {
  const [input, setInput] = useState('')
  const add = () => {
    const t = input.trim().toLowerCase()
    if (t && !tags.includes(t)) { onChange([...tags, t]); setInput('') }
  }
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-1.5">
        {tags.map(tag => (
          <span key={tag} className="tag flex items-center gap-1">
            {tag}
            <button onClick={() => onChange(tags.filter(t => t !== tag))} className="hover:text-red-400 transition-colors ml-0.5">×</button>
          </span>
        ))}
      </div>
      <div className="flex gap-2">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => (e.key === 'Enter' || e.key === ',') && (e.preventDefault(), add())}
          placeholder="Add tag and press Enter..."
          className="input text-xs py-1.5"
        />
        <button onClick={add} className="btn-secondary py-1.5 px-3 text-xs">Add</button>
      </div>
    </div>
  )
}

function ToolEditor({ tools, onChange }) {
  const add = () => onChange([...tools, { name: '', description: '', input_schema: null }])
  const update = (i, field, val) => {
    const next = [...tools]
    next[i] = { ...next[i], [field]: val }
    onChange(next)
  }
  const remove = (i) => onChange(tools.filter((_, idx) => idx !== i))

  return (
    <div className="space-y-2">
      {tools.map((tool, i) => (
        <div key={i} className="bg-gray-950 border border-gray-800 rounded-lg p-3 space-y-2">
          <div className="flex items-center gap-2">
            <Wrench className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0" />
            <input
              value={tool.name}
              onChange={e => update(i, 'name', e.target.value)}
              placeholder="tool_name"
              className="input font-mono text-xs py-1.5 flex-1"
            />
            <button onClick={() => remove(i)} className="p-1 hover:text-red-400 text-gray-600 transition-colors">
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
          <input
            value={tool.description}
            onChange={e => update(i, 'description', e.target.value)}
            placeholder="Tool description..."
            className="input text-xs py-1.5"
          />
        </div>
      ))}
      <button onClick={add} className="btn-secondary text-xs py-1.5 w-full justify-center">
        <Plus className="w-3.5 h-3.5" /> Add Tool
      </button>
    </div>
  )
}

function PromptEditor({ prompts, onChange }) {
  const add = () => onChange([...prompts, { name: '', description: '', template: '' }])
  const update = (i, field, val) => {
    const next = [...prompts]
    next[i] = { ...next[i], [field]: val }
    onChange(next)
  }
  const remove = (i) => onChange(prompts.filter((_, idx) => idx !== i))

  return (
    <div className="space-y-2">
      {prompts.map((prompt, i) => (
        <div key={i} className="bg-gray-950 border border-gray-800 rounded-lg p-3 space-y-2">
          <div className="flex items-center gap-2">
            <Zap className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />
            <input
              value={prompt.name}
              onChange={e => update(i, 'name', e.target.value)}
              placeholder="prompt_name"
              className="input font-mono text-xs py-1.5 flex-1"
            />
            <button onClick={() => remove(i)} className="p-1 hover:text-red-400 text-gray-600 transition-colors">
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
          <input
            value={prompt.description}
            onChange={e => update(i, 'description', e.target.value)}
            placeholder="Prompt description..."
            className="input text-xs py-1.5"
          />
          <textarea
            value={prompt.template}
            onChange={e => update(i, 'template', e.target.value)}
            placeholder="Prompt template with {variables}..."
            className="input text-xs py-1.5 min-h-[60px] resize-none font-mono"
          />
        </div>
      ))}
      <button onClick={add} className="btn-secondary text-xs py-1.5 w-full justify-center">
        <Plus className="w-3.5 h-3.5" /> Add Prompt
      </button>
    </div>
  )
}

function YamlPreview({ form }) {
  const [open, setOpen] = useState(false)
  const [copied, setCopied] = useState(false)
  const yaml = skillToYaml(form)
  const copy = () => {
    navigator.clipboard.writeText(yaml)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  return (
    <div className="border border-gray-800 rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-4 py-2.5 bg-gray-950 hover:bg-gray-900 transition-colors text-left"
      >
        <span className="text-xs font-mono font-semibold text-indigo-400">📄 YAML Preview</span>
        <ChevronDown className={`w-4 h-4 text-gray-500 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div className="relative">
          <pre className="text-xs font-mono p-4 bg-gray-950 text-gray-300 overflow-x-auto max-h-64 leading-relaxed border-t border-gray-800">
            {yaml}
          </pre>
          <button
            onClick={copy}
            className="absolute top-2 right-2 p-1.5 rounded-md bg-gray-800 hover:bg-gray-700 transition-all"
            title="Copy YAML"
          >
            {copied ? <CheckCircle className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5 text-gray-400" />}
          </button>
        </div>
      )}
    </div>
  )
}

export default function AddSkillModal({ existingSkills = [], editSkill = null, onClose, onCreated, onUpdated }) {
  const isEdit = !!editSkill
  const [mode, setMode] = useState('manual')
  const [saving, setSaving] = useState(false)
  const [activeSection, setActiveSection] = useState('basic')

  const [form, setForm] = useState(() => {
    if (editSkill) {
      return {
        name: editSkill.name || '',
        description: editSkill.description || '',
        category: editSkill.category || 'General',
        icon: editSkill.icon || '🔧',
        icon_bg_color: editSkill.icon_bg_color || '#6366f1',
        tags: Array.isArray(editSkill.tags) ? editSkill.tags : [],
        version: editSkill.version || '1.0.0',
        author: editSkill.author || '',
        status: editSkill.status || 'active',
        tools: Array.isArray(editSkill.tools) ? editSkill.tools : [],
        prompts: Array.isArray(editSkill.prompts) ? editSkill.prompts : [],
        resources: Array.isArray(editSkill.resources) ? editSkill.resources : [],
        mcp_config: editSkill.mcp_config || {},
        source: editSkill.source || 'manual',
        metadata: editSkill.metadata || {},
      }
    }
    return {
      name: '', description: '', category: 'General',
      icon: '🔧', icon_bg_color: '#6366f1',
      tags: [], version: '1.0.0', author: '', status: 'active',
      tools: [], prompts: [], resources: [], mcp_config: {}, source: 'manual', metadata: {}
    }
  })

  const update = (field, val) => setForm(f => ({ ...f, [field]: val }))

  const handleLLMApply = (data) => {
    setForm(f => ({ ...f, ...data }))
    setMode('manual')
    setActiveSection('basic')
    toast.success('Skill populated from AI research! Review and save.')
  }

  const handleSave = async () => {
    if (!form.name.trim()) { toast.error('Skill name is required'); return }
    setSaving(true)
    try {
      const payload = {
        ...form,
        tools: form.tools.filter(t => t.name.trim()),
        prompts: form.prompts.filter(p => p.name.trim()),
      }
      if (isEdit) {
        const updated = await skillsApi.update(editSkill.id, payload)
        toast.success(`Skill "${updated.name}" updated!`)
        onUpdated(updated)
      } else {
        const created = await skillsApi.create(payload)
        toast.success(`Skill "${created.name}" created!`)
        onCreated(created)
      }
      onClose()
    } catch (e) {
      const msg = e.response?.data?.detail || e.message || `Failed to ${isEdit ? 'update' : 'create'} skill`
      toast.error(msg)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="modal-overlay animate-fade-in" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal-content max-w-2xl animate-slide-up">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-800 sticky top-0 bg-gray-900 z-10 rounded-t-2xl">
          <div>
            <h2 className="text-lg font-bold text-white">{isEdit ? `Edit: ${editSkill.name}` : 'Add New Skill'}</h2>
            <p className="text-xs text-gray-500 mt-0.5">{isEdit ? 'Update skill details below' : 'Create manually or let Claude design it'}</p>
          </div>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-gray-800 transition-colors">
            <X className="w-4 h-4 text-gray-400" />
          </button>
        </div>

        {/* Mode toggle — only shown when creating */}
        {!isEdit && (
          <div className="flex gap-2 p-4 border-b border-gray-800">
            <button
              onClick={() => setMode('manual')}
              className={`flex-1 py-2 rounded-lg text-sm font-medium transition-all ${
                mode === 'manual' ? 'bg-gray-700 text-white' : 'text-gray-500 hover:text-gray-300 hover:bg-gray-800'
              }`}
            >
              Manual Entry
            </button>
            <button
              onClick={() => setMode('llm')}
              className={`flex-1 py-2 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-2 ${
                mode === 'llm' ? 'bg-indigo-600 text-white' : 'text-gray-500 hover:text-gray-300 hover:bg-gray-800'
              }`}
            >
              <Sparkles className="w-4 h-4" /> AI Research
            </button>
          </div>
        )}

        <div className="p-6">
          {mode === 'llm' ? (
            <LLMResearchPanel
              existingSkills={existingSkills}
              onApply={handleLLMApply}
              onClose={onClose}
            />
          ) : (
            <div className="space-y-6">
              {/* Section tabs */}
              <div className="flex gap-1">
                {['basic', 'icon', 'tools', 'advanced'].map(s => (
                  <button
                    key={s}
                    onClick={() => setActiveSection(s)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors capitalize ${
                      activeSection === s ? 'bg-indigo-600 text-white' : 'text-gray-500 hover:text-gray-300 hover:bg-gray-800'
                    }`}
                  >
                    {s === 'icon' ? '🎨 Icon' : s.charAt(0).toUpperCase() + s.slice(1)}
                  </button>
                ))}
              </div>

              {activeSection === 'basic' && (
                <div className="space-y-4">
                  <div>
                    <label className="section-header">Skill Name *</label>
                    <input value={form.name} onChange={e => update('name', e.target.value)} placeholder="e.g. Web Scraper" className="input" />
                  </div>
                  <div>
                    <label className="section-header">Description</label>
                    <textarea value={form.description} onChange={e => update('description', e.target.value)} placeholder="What does this skill do?" className="input min-h-[80px] resize-none" />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="section-header">Category</label>
                      <select value={form.category} onChange={e => update('category', e.target.value)} className="input">
                        {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
                      </select>
                    </div>
                    <div>
                      <label className="section-header">Version</label>
                      <input value={form.version} onChange={e => update('version', e.target.value)} placeholder="1.0.0" className="input font-mono" />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="section-header">Author</label>
                      <input value={form.author} onChange={e => update('author', e.target.value)} placeholder="Your name" className="input" />
                    </div>
                    <div>
                      <label className="section-header">Status</label>
                      <select value={form.status} onChange={e => update('status', e.target.value)} className="input">
                        <option value="active">Active</option>
                        <option value="inactive">Inactive</option>
                        <option value="deprecated">Deprecated</option>
                      </select>
                    </div>
                  </div>
                  <div>
                    <label className="section-header">Tags</label>
                    <TagInput tags={form.tags} onChange={v => update('tags', v)} />
                  </div>
                </div>
              )}

              {activeSection === 'icon' && (
                <IconPicker
                  icon={form.icon}
                  bgColor={form.icon_bg_color}
                  onIconChange={v => update('icon', v)}
                  onBgColorChange={v => update('icon_bg_color', v)}
                />
              )}

              {activeSection === 'tools' && (
                <div className="space-y-4">
                  <div>
                    <label className="section-header">Tools</label>
                    <ToolEditor tools={form.tools} onChange={v => update('tools', v)} />
                  </div>
                  <div>
                    <label className="section-header">Prompts</label>
                    <PromptEditor prompts={form.prompts} onChange={v => update('prompts', v)} />
                  </div>
                </div>
              )}

              {activeSection === 'advanced' && (
                <div className="space-y-4">
                  <div>
                    <label className="section-header">MCP Config (JSON)</label>
                    <textarea
                      value={JSON.stringify(form.mcp_config, null, 2)}
                      onChange={e => { try { update('mcp_config', JSON.parse(e.target.value)) } catch {} }}
                      className="input font-mono text-xs min-h-[120px] resize-none"
                      placeholder='{"transport": "stdio"}'
                    />
                  </div>
                  <div>
                    <label className="section-header">Source</label>
                    <select value={form.source} onChange={e => update('source', e.target.value)} className="input">
                      <option value="manual">Manual</option>
                      <option value="llm_generated">LLM Generated</option>
                      <option value="imported">Imported</option>
                    </select>
                  </div>
                </div>
              )}

              {/* Preview bar */}
              <div className="flex items-center gap-3 bg-gray-950 border border-gray-800 rounded-xl p-3">
                <div className="w-10 h-10 rounded-xl flex items-center justify-center text-xl flex-shrink-0" style={{ backgroundColor: form.icon_bg_color }}>
                  {form.icon}
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-medium text-white truncate">{form.name || 'Skill Name'}</p>
                  <p className="text-xs text-gray-500">{form.category} · {form.tools.filter(t => t.name).length} tools</p>
                </div>
              </div>

              {/* YAML Preview */}
              <YamlPreview form={form} />
            </div>
          )}
        </div>

        {/* Footer */}
        {mode === 'manual' && (
          <div className="flex gap-3 px-6 pb-6">
            <button onClick={onClose} className="btn-secondary flex-1 justify-center">Cancel</button>
            <button onClick={handleSave} disabled={saving || !form.name.trim()} className="btn-primary flex-1 justify-center">
              {saving ? (isEdit ? 'Saving...' : 'Creating...') : (isEdit ? 'Save Changes' : '+ Create Skill')}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
