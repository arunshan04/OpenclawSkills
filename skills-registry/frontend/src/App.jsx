import { useState, useEffect, useCallback } from 'react'
import { Plus, Search, Filter, Grid, List, RefreshCw, Sparkles, Settings, X, ChevronDown, Zap, Database, Cpu } from 'lucide-react'
import toast from 'react-hot-toast'
import SkillCard from './components/SkillCard'
import SkillDetailModal from './components/SkillDetailModal'
import AddSkillModal from './components/AddSkillModal'
import { skillsApi } from './services/api'

function StatCard({ label, value, icon: Icon, color }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex items-center gap-3">
      <div className={`w-10 h-10 rounded-lg ${color} flex items-center justify-center flex-shrink-0`}>
        <Icon className="w-5 h-5" />
      </div>
      <div>
        <p className="text-2xl font-bold text-white leading-none">{value ?? '—'}</p>
        <p className="text-xs text-gray-500 mt-0.5">{label}</p>
      </div>
    </div>
  )
}

const SORT_OPTIONS = [
  { value: 'name', label: 'Name (A–Z)' },
  { value: 'name_desc', label: 'Name (Z–A)' },
  { value: 'category', label: 'Category' },
  { value: 'created', label: 'Newest First' },
]

export default function App() {
  const [skills, setSkills] = useState([])
  const [categories, setCategories] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [filterCategory, setFilterCategory] = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const [sort, setSort] = useState('name')
  const [view, setView] = useState('grid')
  const [selectedSkill, setSelectedSkill] = useState(null)
  const [showAdd, setShowAdd] = useState(false)
  const [editSkill, setEditSkill] = useState(null)

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const [skillsData, catsData, statsData] = await Promise.all([
        skillsApi.list({ search: search || undefined, category: filterCategory || undefined, status: filterStatus || undefined }),
        skillsApi.categories(),
        skillsApi.stats(),
      ])
      setSkills(skillsData)
      setCategories(catsData)
      setStats(statsData)
    } catch (e) {
      toast.error('Failed to load skills. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }, [search, filterCategory, filterStatus])

  useEffect(() => { loadData() }, [loadData])

  const handleDelete = async (id) => {
    await skillsApi.delete(id)
    toast.success('Skill deleted')
    setSkills(prev => prev.filter(s => s.id !== id))
    setStats(prev => prev ? { ...prev, total: prev.total - 1, active: prev.active - 1 } : prev)
  }

  const handleEdit = (skill) => {
    setSelectedSkill(null)
    setEditSkill(skill)
    setShowAdd(true)
  }

  const handleCreated = (skill) => {
    setSkills(prev => [skill, ...prev])
    loadData()
  }

  const handleUpdated = (skill) => {
    setSkills(prev => prev.map(s => s.id === skill.id ? skill : s))
    loadData()
  }

  const sortedSkills = [...skills].sort((a, b) => {
    if (sort === 'name') return a.name.localeCompare(b.name)
    if (sort === 'name_desc') return b.name.localeCompare(a.name)
    if (sort === 'category') return a.category.localeCompare(b.category)
    if (sort === 'created') return new Date(b.created_at) - new Date(a.created_at)
    return 0
  })

  return (
    <div className="min-h-screen bg-gray-950">
      {/* Top Nav */}
      <header className="sticky top-0 z-40 bg-gray-950/90 backdrop-blur-md border-b border-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center text-lg">🧩</div>
            <div>
              <span className="font-bold text-white text-sm">Skills Registry</span>
              <span className="ml-2 text-xs text-gray-500 hidden sm:inline">MCP Skill Catalog</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <a href="http://localhost:8000/docs" target="_blank" rel="noreferrer"
              className="hidden sm:flex btn-secondary text-xs py-1.5">
              <Settings className="w-3.5 h-3.5" /> API Docs
            </a>
            <button onClick={() => setShowAdd(true)} className="btn-primary text-xs">
              <Plus className="w-3.5 h-3.5" /> Add Skill
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-6">
        {/* Stats row */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <StatCard label="Total Skills" value={stats?.total} icon={Database} color="bg-indigo-900/50 text-indigo-300" />
          <StatCard label="Active" value={stats?.active} icon={Zap} color="bg-emerald-900/50 text-emerald-300" />
          <StatCard label="Categories" value={stats?.categories} icon={Filter} color="bg-amber-900/50 text-amber-300" />
          <StatCard label="AI Generated" value={stats?.llm_generated} icon={Sparkles} color="bg-purple-900/50 text-purple-300" />
        </div>

        {/* Search & Filters */}
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
            <input
              type="text"
              placeholder="Search skills by name, description, or tag..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="input pl-9"
            />
            {search && (
              <button onClick={() => setSearch('')} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300">
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          <div className="flex gap-2 flex-wrap">
            {/* Category filter */}
            <div className="relative">
              <select
                value={filterCategory}
                onChange={e => setFilterCategory(e.target.value)}
                className="input pr-8 appearance-none text-sm min-w-[130px]"
              >
                <option value="">All Categories</option>
                {categories.map(c => (
                  <option key={c.category} value={c.category}>{c.category} ({c.count})</option>
                ))}
              </select>
              <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 pointer-events-none" />
            </div>

            {/* Status filter */}
            <div className="relative">
              <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)} className="input pr-8 appearance-none text-sm min-w-[110px]">
                <option value="">All Status</option>
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
                <option value="deprecated">Deprecated</option>
              </select>
              <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 pointer-events-none" />
            </div>

            {/* Sort */}
            <div className="relative">
              <select value={sort} onChange={e => setSort(e.target.value)} className="input pr-8 appearance-none text-sm min-w-[130px]">
                {SORT_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
              <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 pointer-events-none" />
            </div>

            {/* View toggle */}
            <div className="flex rounded-lg border border-gray-700 overflow-hidden">
              <button onClick={() => setView('grid')} className={`p-2 transition-colors ${view === 'grid' ? 'bg-gray-700 text-white' : 'text-gray-500 hover:text-gray-300 hover:bg-gray-800'}`}>
                <Grid className="w-4 h-4" />
              </button>
              <button onClick={() => setView('list')} className={`p-2 transition-colors ${view === 'list' ? 'bg-gray-700 text-white' : 'text-gray-500 hover:text-gray-300 hover:bg-gray-800'}`}>
                <List className="w-4 h-4" />
              </button>
            </div>

            <button onClick={loadData} className="btn-secondary px-3" title="Refresh">
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {/* Active filters */}
        {(filterCategory || filterStatus || search) && (
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs text-gray-500">Filters:</span>
            {search && <span className="tag flex items-center gap-1">"{search}" <button onClick={() => setSearch('')} className="hover:text-red-400">×</button></span>}
            {filterCategory && <span className="tag flex items-center gap-1">{filterCategory} <button onClick={() => setFilterCategory('')} className="hover:text-red-400">×</button></span>}
            {filterStatus && <span className="tag flex items-center gap-1">{filterStatus} <button onClick={() => setFilterStatus('')} className="hover:text-red-400">×</button></span>}
            <button onClick={() => { setSearch(''); setFilterCategory(''); setFilterStatus('') }} className="text-xs text-gray-500 hover:text-gray-300">Clear all</button>
          </div>
        )}

        {/* Skill Grid / List */}
        {loading ? (
          <div className="flex flex-col items-center justify-center py-24 gap-4">
            <div className="w-10 h-10 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
            <p className="text-sm text-gray-500">Loading skills...</p>
          </div>
        ) : sortedSkills.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-24 gap-4">
            <div className="text-6xl">🧩</div>
            <p className="text-lg font-medium text-gray-400">No skills found</p>
            <p className="text-sm text-gray-600 text-center max-w-sm">
              {search || filterCategory || filterStatus
                ? 'Try adjusting your filters or search query.'
                : 'Add your first skill to get started.'}
            </p>
            <button onClick={() => setShowAdd(true)} className="btn-primary">
              <Plus className="w-4 h-4" /> Add First Skill
            </button>
          </div>
        ) : (
          <>
            <p className="text-xs text-gray-600">{sortedSkills.length} skill{sortedSkills.length !== 1 ? 's' : ''}</p>
            <div className={
              view === 'grid'
                ? 'grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4'
                : 'space-y-2'
            }>
              {sortedSkills.map(skill => (
                <SkillCard
                  key={skill.id}
                  skill={skill}
                  onClick={setSelectedSkill}
                />
              ))}
            </div>
          </>
        )}

        {/* MCP info footer */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 mt-8">
          <div className="flex items-start gap-3">
            <Cpu className="w-5 h-5 text-indigo-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-semibold text-gray-200">MCP Server</p>
              <p className="text-xs text-gray-500 mt-0.5">
                Connect your MCP client to{' '}
                <code className="font-mono text-indigo-300 bg-indigo-950/50 px-1 rounded">http://localhost:8000/mcp</code>{' '}
                to access all {stats?.active || 0} active skills via the Model Context Protocol.
              </p>
            </div>
          </div>
        </div>
      </main>

      {/* Modals */}
      {selectedSkill && (
        <SkillDetailModal
          skill={selectedSkill}
          onClose={() => setSelectedSkill(null)}
          onDelete={handleDelete}
          onEdit={handleEdit}
        />
      )}

      {showAdd && (
        <AddSkillModal
          existingSkills={skills}
          editSkill={editSkill}
          onClose={() => { setShowAdd(false); setEditSkill(null) }}
          onCreated={handleCreated}
          onUpdated={handleUpdated}
        />
      )}
    </div>
  )
}
