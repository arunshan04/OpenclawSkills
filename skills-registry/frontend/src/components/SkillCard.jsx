import { Wrench, Zap, Tag, Clock, User } from 'lucide-react'

const STATUS_STYLES = {
  active: 'status-active',
  inactive: 'status-inactive',
  deprecated: 'status-deprecated',
}

const SOURCE_STYLES = {
  llm_generated: 'source-llm',
  manual: 'source-manual',
}

export default function SkillCard({ skill, onClick }) {
  const toolCount = skill.tools?.length || 0
  const promptCount = skill.prompts?.length || 0

  return (
    <button
      onClick={() => onClick(skill)}
      className="card p-5 text-left w-full group hover:shadow-lg hover:shadow-black/20 hover:-translate-y-0.5 transition-all duration-200 animate-fade-in"
    >
      {/* Header */}
      <div className="flex items-start gap-3 mb-3">
        <div
          className="w-12 h-12 rounded-xl flex items-center justify-center text-2xl flex-shrink-0 shadow-md group-hover:shadow-lg transition-shadow"
          style={{ backgroundColor: skill.icon_bg_color || '#6366f1' }}
        >
          {skill.icon || '🔧'}
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="font-semibold text-gray-100 text-sm leading-tight truncate group-hover:text-white transition-colors">
            {skill.name}
          </h3>
          <p className="text-xs text-gray-500 mt-0.5">{skill.category}</p>
        </div>
        <span className={`badge flex-shrink-0 ${STATUS_STYLES[skill.status] || STATUS_STYLES.inactive}`}>
          {skill.status}
        </span>
      </div>

      {/* Description */}
      <p className="text-xs text-gray-400 line-clamp-2 mb-3 leading-relaxed">
        {skill.description || 'No description provided.'}
      </p>

      {/* Tags */}
      {skill.tags?.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-3">
          {skill.tags.slice(0, 3).map(tag => (
            <span key={tag} className="tag">{tag}</span>
          ))}
          {skill.tags.length > 3 && (
            <span className="tag text-gray-500">+{skill.tags.length - 3}</span>
          )}
        </div>
      )}

      {/* Footer stats */}
      <div className="flex items-center justify-between pt-2 border-t border-gray-800">
        <div className="flex items-center gap-3">
          {toolCount > 0 && (
            <span className="flex items-center gap-1 text-xs text-gray-500">
              <Wrench className="w-3 h-3" />
              {toolCount} tool{toolCount !== 1 ? 's' : ''}
            </span>
          )}
          {promptCount > 0 && (
            <span className="flex items-center gap-1 text-xs text-gray-500">
              <Zap className="w-3 h-3" />
              {promptCount} prompt{promptCount !== 1 ? 's' : ''}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {skill.source === 'llm_generated' && (
            <span className={`badge ${SOURCE_STYLES.llm_generated}`}>
              ✨ AI
            </span>
          )}
          <span className="text-xs text-gray-600 font-mono">v{skill.version || '1.0.0'}</span>
        </div>
      </div>
    </button>
  )
}
