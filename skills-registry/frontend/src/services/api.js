import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

export const skillsApi = {
  list: (params = {}) => api.get('/skills', { params }).then(r => r.data),
  get: (id) => api.get(`/skills/${id}`).then(r => r.data),
  create: (data) => api.post('/skills', data).then(r => r.data),
  update: (id, data) => api.put(`/skills/${id}`, data).then(r => r.data),
  delete: (id) => api.delete(`/skills/${id}`),
  categories: () => api.get('/skills/categories').then(r => r.data),
  stats: () => api.get('/skills/stats').then(r => r.data),
  research: (data) => api.post('/skills/research', data).then(r => r.data),
  executeTool: (skillId, toolName, params = {}) =>
    api.post(`/skills/${skillId}/tools/${toolName}/execute`, { params }).then(r => r.data),
}

export default api
