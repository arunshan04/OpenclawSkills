import { useState } from 'react'
import { Search } from 'lucide-react'

const ICON_CATEGORIES = {
  'Tech & Dev': ['💻', '🖥️', '🖱️', '⌨️', '📱', '💾', '💿', '📡', '🔌', '🖨️', '⌚', '📷', '🎮', '🕹️', '🔋'],
  'AI & Data': ['🤖', '🧠', '💡', '✨', '🌟', '⚡', '🔥', '🌀', '🗄️', '📊', '📈', '📉', '🧮', '🔢', '🧬'],
  'Security': ['🛡️', '🔐', '🔑', '🔒', '🔓', '⚠️', '🚨', '🔍', '👁️', '🕵️', '⚔️', '🛡', '🪖', '🔏', '🗝️'],
  'Research': ['🔬', '🔭', '📚', '📖', '🗺️', '🧭', '📝', '✏️', '🖊️', '📋', '📄', '🗂️', '📑', '🗃️', '📌'],
  'Communication': ['💬', '📢', '📣', '📨', '📩', '✉️', '📧', '📲', '📞', '☎️', '📟', '📠', '🔔', '🔕', '💌'],
  'Creative': ['🎨', '🖌️', '✏️', '🎭', '🎬', '🎵', '🎶', '🎤', '🎸', '🎹', '📸', '🖼️', '🎨', '✨', '🌈'],
  'Productivity': ['📋', '✅', '☑️', '📅', '📆', '⏰', '⏱️', '🗓️', '📌', '📍', '🏷️', '📎', '🖇️', '✂️', '🗑️'],
  'Cloud & Network': ['☁️', '🌐', '🌍', '🌎', '🌏', '🌩️', '🌦️', '📡', '🔗', '🕸️', '🏗️', '🚀', '🛸', '🌊', '💻'],
  'Finance': ['💰', '💵', '💴', '💶', '💷', '💳', '🏦', '📊', '💹', '🪙', '💎', '🏧', '💸', '🤑', '📈'],
  'Health & Science': ['🏥', '💊', '🩺', '🩻', '🧬', '🔬', '⚗️', '🧪', '🩸', '🧫', '🦠', '💉', '🩹', '❤️‍🩹', '🫀'],
  'Tools & Settings': ['🔧', '🔨', '🪛', '⚙️', '🛠️', '🔩', '🪤', '🔫', '🪝', '🧲', '🪜', '🔭', '🔬', '🗜️', '🧰'],
  'Symbols': ['⚡', '🔥', '💧', '🌊', '🌪️', '⭐', '🌟', '💫', '✨', '🎯', '🏆', '🥇', '🎖️', '🏅', '🎗️'],
}

const BG_COLORS = [
  { name: 'Indigo', value: '#6366f1' },
  { name: 'Blue', value: '#3b82f6' },
  { name: 'Emerald', value: '#10b981' },
  { name: 'Amber', value: '#f59e0b' },
  { name: 'Red', value: '#ef4444' },
  { name: 'Pink', value: '#ec4899' },
  { name: 'Purple', value: '#8b5cf6' },
  { name: 'Cyan', value: '#06b6d4' },
  { name: 'Orange', value: '#f97316' },
  { name: 'Lime', value: '#84cc16' },
  { name: 'Rose', value: '#f43f5e' },
  { name: 'Teal', value: '#14b8a6' },
  { name: 'Sky', value: '#0ea5e9' },
  { name: 'Violet', value: '#7c3aed' },
  { name: 'Gray', value: '#6b7280' },
]

export default function IconPicker({ icon, bgColor, onIconChange, onBgColorChange }) {
  const [search, setSearch] = useState('')
  const [activeCategory, setActiveCategory] = useState('Tech & Dev')

  const filteredIcons = search
    ? Object.values(ICON_CATEGORIES).flat().filter((_, i) =>
        Object.entries(ICON_CATEGORIES).some(([cat, icons]) =>
          cat.toLowerCase().includes(search.toLowerCase()) && icons.includes(_)
        ) || true
      ).slice(0, 60)
    : ICON_CATEGORIES[activeCategory] || []

  const allIcons = search
    ? [...new Set(Object.values(ICON_CATEGORIES).flat())].filter(() => true)
    : null

  const displayIcons = search
    ? [...new Set(Object.values(ICON_CATEGORIES).flat())]
    : ICON_CATEGORIES[activeCategory] || []

  return (
    <div className="space-y-4">
      {/* Preview */}
      <div className="flex items-center gap-4">
        <div
          className="w-16 h-16 rounded-2xl flex items-center justify-center text-3xl shadow-lg flex-shrink-0 transition-all duration-200"
          style={{ backgroundColor: bgColor }}
        >
          {icon}
        </div>
        <div>
          <p className="text-sm font-medium text-gray-300">Icon Preview</p>
          <p className="text-xs text-gray-500 mt-0.5">Selected icon with background color</p>
        </div>
      </div>

      {/* BG Color Picker */}
      <div>
        <p className="section-header">Background Color</p>
        <div className="flex flex-wrap gap-2">
          {BG_COLORS.map(c => (
            <button
              key={c.value}
              onClick={() => onBgColorChange(c.value)}
              className={`w-7 h-7 rounded-lg transition-all duration-150 ${bgColor === c.value ? 'ring-2 ring-white ring-offset-2 ring-offset-gray-900 scale-110' : 'hover:scale-105'}`}
              style={{ backgroundColor: c.value }}
              title={c.name}
            />
          ))}
          <label className="w-7 h-7 rounded-lg border-2 border-dashed border-gray-600 hover:border-gray-400 cursor-pointer flex items-center justify-center transition-colors" title="Custom color">
            <input
              type="color"
              className="opacity-0 absolute w-0 h-0"
              value={bgColor}
              onChange={e => onBgColorChange(e.target.value)}
            />
            <span className="text-gray-500 text-xs">+</span>
          </label>
        </div>
      </div>

      {/* Icon Search */}
      <div>
        <p className="section-header">Choose Icon</p>
        <div className="relative mb-3">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            type="text"
            placeholder="Search icons..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="input pl-9"
          />
        </div>

        {/* Category tabs */}
        {!search && (
          <div className="flex gap-1 flex-wrap mb-3">
            {Object.keys(ICON_CATEGORIES).map(cat => (
              <button
                key={cat}
                onClick={() => setActiveCategory(cat)}
                className={`px-2 py-1 rounded-md text-xs font-medium transition-colors ${
                  activeCategory === cat
                    ? 'bg-indigo-600 text-white'
                    : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
        )}

        {/* Icon Grid */}
        <div className="grid grid-cols-8 gap-1 max-h-40 overflow-y-auto p-1 bg-gray-950 rounded-lg border border-gray-800">
          {displayIcons.map((emoji, i) => (
            <button
              key={`${emoji}-${i}`}
              onClick={() => onIconChange(emoji)}
              className={`w-9 h-9 rounded-lg text-xl flex items-center justify-center transition-all duration-100 hover:scale-110 ${
                icon === emoji ? 'bg-indigo-600/30 ring-2 ring-indigo-500' : 'hover:bg-gray-800'
              }`}
              title={emoji}
            >
              {emoji}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
