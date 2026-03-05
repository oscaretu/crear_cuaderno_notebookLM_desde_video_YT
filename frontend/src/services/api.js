const API_BASE = '/api'

export const api = {
  // Auth endpoints
  async getAuthStatus() {
    const response = await fetch(`${API_BASE}/auth/status`)
    if (!response.ok) throw new Error('Error checking auth status')
    return response.json()
  },

  async getProfiles(username = 'oscar') {
    const response = await fetch(`${API_BASE}/auth/profiles?username=${username}`)
    if (!response.ok) throw new Error('Error loading profiles')
    return response.json()
  },

  async extractCookies(username, profile = null) {
    const body = { username }
    if (profile) body.profile = profile
    
    const response = await fetch(`${API_BASE}/auth/extract-cookies`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })
    if (!response.ok) throw new Error('Error extracting cookies')
    return response.json()
  },

  // Notebook endpoints
  async getNotebooks() {
    const response = await fetch(`${API_BASE}/notebooks`)
    if (!response.ok) throw new Error('Error loading notebooks')
    return response.json()
  },

  async getNotebook(notebookId, language = 'es') {
    const response = await fetch(`${API_BASE}/notebooks/${notebookId}?language=${language}`)
    if (!response.ok) throw new Error('Error loading notebook')
    return response.json()
  },

  async createNotebook(youtubeUrl, language = 'es', artifacts = null) {
    const body = { 
      youtube_url: youtubeUrl,
      language
    }
    if (artifacts) body.artifacts = artifacts
    
    const response = await fetch(`${API_BASE}/notebooks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })
    
    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Error creating notebook')
    }
    return response.json()
  },

  async generateArtifacts(notebookId, artifactTypes, language = 'es') {
    const response = await fetch(`${API_BASE}/notebooks/${notebookId}/artifacts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        artifact_types: artifactTypes,
        language
      })
    })
    if (!response.ok) throw new Error('Error generating artifacts')
    return response.json()
  },

  // Health check
  async healthCheck() {
    const response = await fetch(`${API_BASE}/health`)
    return response.json()
  }
}
