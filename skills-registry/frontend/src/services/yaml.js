function yamlStr(val) {
  if (val === null || val === undefined) return 'null'
  if (typeof val === 'string') return val.includes('\n') ? `|\n  ${val.replace(/\n/g, '\n  ')}` : val
  return String(val)
}

function yamlList(items, indent = '') {
  if (!items?.length) return '[]'
  return '\n' + items.map(item =>
    typeof item === 'string'
      ? `${indent}  - ${item}`
      : `${indent}  - ${Object.entries(item).map(([k, v], i) =>
          i === 0 ? `${k}: ${yamlStr(v)}` : `${indent}    ${k}: ${yamlStr(v)}`
        ).join('\n')}`
  ).join('\n')
}

export function skillToYaml(skill) {
  const tags = Array.isArray(skill.tags) ? skill.tags : []
  const tools = Array.isArray(skill.tools) ? skill.tools : []
  const prompts = Array.isArray(skill.prompts) ? skill.prompts : []
  const resources = Array.isArray(skill.resources) ? skill.resources : []
  const mcp = typeof skill.mcp_config === 'object' ? skill.mcp_config : {}

  const toolsYaml = tools.length === 0 ? '[]' : '\n' + tools.map(t => [
    `  - name: ${t.name || ''}`,
    `    description: ${yamlStr(t.description || '')}`,
    t.input_schema ? `    input_schema: ${JSON.stringify(t.input_schema)}` : null,
    t.code ? `    code: |\n      ${t.code.replace(/\n/g, '\n      ')}` : null,
  ].filter(Boolean).join('\n')).join('\n')

  const promptsYaml = prompts.length === 0 ? '[]' : '\n' + prompts.map(p => [
    `  - name: ${p.name || ''}`,
    `    description: ${yamlStr(p.description || '')}`,
    p.template ? `    template: |\n      ${p.template.replace(/\n/g, '\n      ')}` : null,
  ].filter(Boolean).join('\n')).join('\n')

  const resourcesYaml = resources.length === 0 ? '[]' : '\n' + resources.map(r => [
    `  - uri: ${r.uri}`,
    `    name: ${r.name}`,
    r.description ? `    description: ${r.description}` : null,
  ].filter(Boolean).join('\n')).join('\n')

  const mcpLines = Object.entries(mcp).map(([k, v]) => `  ${k}: ${yamlStr(v)}`).join('\n')

  return `---
name: ${skill.name || ''}
description: ${yamlStr(skill.description || '')}
category: ${skill.category || 'General'}
icon: ${skill.icon || '🔧'}
icon_bg_color: "${skill.icon_bg_color || '#6366f1'}"
version: ${skill.version || '1.0.0'}
author: ${skill.author || ''}
status: ${skill.status || 'active'}
source: ${skill.source || 'manual'}
tags:${tags.length ? '\n' + tags.map(t => `  - ${t}`).join('\n') : ' []'}
tools:${toolsYaml}
prompts:${promptsYaml}
resources:${resourcesYaml}
mcp_config:${Object.keys(mcp).length ? '\n' + mcpLines : ' {}'}
---`
}
