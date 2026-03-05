import { useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import { api } from './services/api'

const ARTIFACT_TYPES = [
  { id: 'report', name: 'Informe', limited: false },
  { id: 'mind_map', name: 'Mapa Mental', limited: false },
  { id: 'data_table', name: 'Tabla de Datos', limited: false },
  { id: 'slides', name: 'Presentación', limited: true },
  { id: 'infographic', name: 'Infografía', limited: true },
  { id: 'quiz', name: 'Cuestionario', limited: true },
  { id: 'flashcards', name: 'Tarjetas', limited: true },
  { id: 'audio', name: 'Audio', limited: true },
  { id: 'video', name: 'Video', limited: true },
]

const DEFAULT_ARTIFACTS = ['report', 'mind_map', 'data_table', 'quiz', 'flashcards']

function App() {
  const [activeTab, setActiveTab] = useState('notebooks')
  const [authStatus, setAuthStatus] = useState(null)
  const [notebooks, setNotebooks] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)
  const [authError, setAuthError] = useState(false)
  
  // Create notebook form
  const [youtubeUrl, setYoutubeUrl] = useState('')
  const [language, setLanguage] = useState('es')
  const [selectedArtifacts, setSelectedArtifacts] = useState(DEFAULT_ARTIFACTS)
  const [creating, setCreating] = useState(false)
  
  // Notebook detail
  const [selectedNotebook, setSelectedNotebook] = useState(null)
  const [notebookDetail, setNotebookDetail] = useState(null)
  const [loadingDetail, setLoadingDetail] = useState(false)
  
  // Sort state for notebooks list
  const [sortOrder, setSortOrder] = useState('alpha') // 'alpha', 'alpha-rev', 'date-asc', 'date-desc'
  
  // Search state
  const [searchQuery, setSearchQuery] = useState('')
  
  // Auth form
  const [username, setUsername] = useState('oscar')
  const [selectedProfile, setSelectedProfile] = useState('')
  const [profiles, setProfiles] = useState([])
  const [extracting, setExtracting] = useState(false)
  const [showMarkdownModal, setShowMarkdownModal] = useState(null) // { title, content }
  const [copiedId, setCopiedId] = useState(null) // ID of artifact being copied

  // Global loading state for cursor
  const isLoading = loading || loadingDetail || creating || extracting

  useEffect(() => {
    checkAuthStatus()
    loadProfiles()
  }, [])

  useEffect(() => {
    if (activeTab === 'notebooks') {
      loadNotebooks()
    }
  }, [activeTab])

  useEffect(() => {
    if (activeTab === 'auth') {
      loadProfiles()
    }
  }, [activeTab])

  const checkAuthStatus = async () => {
    try {
      const data = await api.getAuthStatus()
      setAuthStatus(data)
    } catch (err) {
      setAuthStatus({ authenticated: false, message: 'Error checking status' })
    }
  }

  const loadProfiles = async () => {
    try {
      const data = await api.getProfiles(username)
      setProfiles(data)
    } catch (err) {
      console.error('Error loading profiles:', err)
    }
  }

  const loadNotebooks = async () => {
    setLoading(true)
    setError(null)
    setAuthError(false)
    try {
      const data = await api.getNotebooks()
      setNotebooks(data)
    } catch (err) {
      const errorMsg = err.message || String(err)
      setError(errorMsg)
      // Detect authentication errors
      if (errorMsg.includes('Authentication') || errorMsg.includes('authenticate') || 
          errorMsg.includes('login') || errorMsg.includes('expired') ||
          errorMsg.includes('Google') || errorMsg.includes('notebooklm')) {
        setAuthError(true)
      }
    } finally {
      setLoading(false)
    }
  }

  const loadNotebookDetail = async (notebookId) => {
    setLoadingDetail(true)
    setError(null)
    setSelectedNotebook(notebookId)  // Show detail view immediately
    setNotebookDetail(null)  // Clear previous data
    try {
      const data = await api.getNotebook(notebookId, language)
      setNotebookDetail(data)
    } catch (err) {
      const errorMsg = err.message || String(err)
      setError(errorMsg)
      // If auth error, show auth error state
      if (errorMsg.includes('Authentication') || errorMsg.includes('authenticate') || 
          errorMsg.includes('login') || errorMsg.includes('expired') ||
          errorMsg.includes('Google') || errorMsg.includes('notebooklm')) {
        setAuthError(true)
      }
    } finally {
      setLoadingDetail(false)
    }
  }

  const handleExtractCookies = async () => {
    setExtracting(true)
    setError(null)
    setSuccess(null)
    try {
      const result = await api.extractCookies(username, selectedProfile)
      if (result.success) {
        setSuccess(result.message)
        checkAuthStatus()
      } else {
        setError(result.message)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setExtracting(false)
    }
  }

  const handleCreateNotebook = async () => {
    if (!youtubeUrl) {
      setError('Por favor introduce una URL de YouTube')
      return
    }
    
    setCreating(true)
    setError(null)
    setSuccess(null)
    try {
      const result = await api.createNotebook(youtubeUrl, language, selectedArtifacts)
      setSuccess(`Cuaderno creado: ${result.notebook.title}`)
      setYoutubeUrl('')
      loadNotebooks()
    } catch (err) {
      setError(err.message)
    } finally {
      setCreating(false)
    }
  }

  const handleGenerateArtifacts = async (notebookId, artifactTypes) => {
    setLoadingDetail(true)
    setError(null)
    setSuccess(null)
    try {
      const result = await api.generateArtifacts(notebookId, artifactTypes, language)
      setSuccess(result.message)
      // Force refresh the detail view after a short delay to let the backend process
      setTimeout(() => {
        loadNotebookDetail(notebookId)
      }, 1000)
    } catch (err) {
      setError(err.message)
      if (err.message.includes('autenticación') || err.message.includes('expired')) {
        setAuthError(true)
      }
    } finally {
      setLoadingDetail(false)
    }
  }

  const handleCopyMarkdown = async (content, artifactId) => {
    try {
      await navigator.clipboard.writeText(content)
      setCopiedId(artifactId)
      setTimeout(() => setCopiedId(null), 2000)
    } catch (err) {
      console.error('Error copying:', err)
    }
  }

  const handleSelectArtifact = (artifactId) => {
    setSelectedArtifacts(prev => 
      prev.includes(artifactId)
        ? prev.filter(a => a !== artifactId)
        : [...prev, artifactId]
    )
  }

  // Get sorted notebooks based on sortOrder and filtered by search
  const getSortedNotebooks = () => {
    let filtered = [...notebooks]
    
    // Filter by search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase()
      filtered = filtered.filter(nb => 
        nb.title.toLowerCase().includes(query) ||
        nb.id.toLowerCase().includes(query)
      )
    }
    
    // Sort
    switch (sortOrder) {
      case 'alpha':
        return filtered.sort((a, b) => a.title.localeCompare(b.title))
      case 'alpha-rev':
        return filtered.sort((a, b) => b.title.localeCompare(a.title))
      case 'date-asc':
        return filtered.sort((a, b) => new Date(a.created_at || 0) - new Date(b.created_at || 0))
      case 'date-desc':
        return filtered.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0))
      default:
        return filtered
    }
  }

  const renderArtifactCard = (artifact, artifactList, notebookId) => {
    const isAvailable = artifactList && artifactList.length > 0
    const artifactInfo = ARTIFACT_TYPES.find(a => a.id === artifact)
    const isReport = artifact === 'report'
    
    return (
      <div key={artifact} className={`artifact-card ${isAvailable ? 'available' : 'not-available'}`}>
        <h4>{artifactInfo?.name || artifact} {isAvailable && <span style={{ fontWeight: 'normal', fontSize: '0.8em' }}>({artifactList.length})</span>}</h4>
        <p className={`status ${isAvailable ? 'available' : 'not-available'}`}>
          {isAvailable ? `✓ ${artifactList.length} disponible(s)` : '✗ No disponible'}
          {artifactInfo?.limited && ' (límite diario)'}
        </p>
        {!isAvailable && (
          <button 
            className="btn btn-secondary"
            onClick={() => handleGenerateArtifacts(notebookId, [artifact])}
            disabled={loadingDetail}
          >
            Generar
          </button>
        )}
        {isAvailable && (
          <div style={{ marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {artifactList.map((art, idx) => {
              const hasDownloadUrl = art.download_url && !art.download_url.startsWith('#')
              const hasMarkdown = isReport && art.markdown_content
              
              if (hasMarkdown) {
                return (
                  <div key={idx} style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <span style={{ fontSize: '0.85em', color: '#666' }}>{art.name}</span>
                    <div style={{ display: 'flex', gap: '4px' }}>
                      <button
                        className="btn btn-secondary"
                        style={{ flex: 1, fontSize: '0.8em', padding: '6px 8px' }}
                        onClick={() => setShowMarkdownModal({ title: art.name, content: art.markdown_content })}
                      >
                        Ver
                      </button>
                      <button
                        className="btn btn-primary"
                        style={{ flex: 1, fontSize: '0.8em', padding: '6px 8px' }}
                        onClick={() => handleCopyMarkdown(art.markdown_content, art.id)}
                      >
                        {copiedId === art.id ? '✓ Copiado' : '📋 Copiar'}
                      </button>
                    </div>
                  </div>
                )
              }
              
              if (hasDownloadUrl) {
                return (
                  <a 
                    key={idx}
                    href={art.download_url}
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="btn btn-primary"
                    style={{ textDecoration: 'none', fontSize: '0.9em', padding: '8px 16px' }}
                  >
                    {art.name || `Descargar #${idx + 1}`}
                  </a>
                )
              }
              
              return (
                <span key={idx} style={{ fontSize: '0.85em', color: '#666' }}>
                  {art.name || `Artifact #${idx + 1}`}
                </span>
              )
            })}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className={isLoading ? 'loading' : ''}>
      <header className="header">
        <div className="header-content">
          <h1>📚 NotebookLM</h1>
          <div className="auth-status">
            <span className={`auth-badge ${authStatus?.authenticated ? 'authenticated' : 'not-authenticated'}`}>
              {authStatus?.authenticated ? '✓ Autenticado' : '✗ No autenticado'}
            </span>
          </div>
        </div>
      </header>

      <div className="container">
        <div className="tabs">
          <button 
            className={`tab ${activeTab === 'notebooks' ? 'active' : ''}`}
            onClick={() => { setActiveTab('notebooks'); setSelectedNotebook(null); setError(null); setSuccess(null); }}
          >
            Cuadernos
          </button>
          <button 
            className={`tab ${activeTab === 'create' ? 'active' : ''}`}
            onClick={() => { setActiveTab('create'); setError(null); setSuccess(null); }}
          >
            Crear Cuaderno
          </button>
          <button 
            className={`tab ${activeTab === 'auth' ? 'active' : ''}`}
            onClick={() => { setActiveTab('auth'); setError(null); setSuccess(null); setAuthError(false); }}
          >
            Autenticación
          </button>
        </div>

        {error && <div className="alert alert-error">{error}</div>}
        {success && <div className="alert alert-success">{success}</div>}
        
        {authError && (
          <div className="alert alert-error" style={{ background: '#fef3c7', color: '#92400e', borderLeftColor: '#f59e0b' }}>
            <strong>⚠️ Error de autenticación</strong>
            <p style={{ marginTop: '8px' }}>
              Las cookies de Google han expirado o no están configuradas. 
              Ve a la pestaña "Autenticación" para extraer nuevas cookies de Firefox.
            </p>
            <button 
              className="btn" 
              style={{ marginTop: '12px', background: '#f59e0b', color: 'white' }}
              onClick={() => { setActiveTab('auth'); setAuthError(false); }}
            >
              Ir a Autenticación
            </button>
          </div>
        )}

        {activeTab === 'auth' && (
          <div className="card">
            <h2>Extraer Cookies de Firefox</h2>
            <p style={{ marginBottom: '16px', color: '#666' }}>
              Extrae las cookies de Google desde Firefox para autenticarte en NotebookLM.
            </p>
            
            <div className="form-group">
              <label>Usuario de Windows</label>
              <input 
                type="text" 
                value={username} 
                onChange={(e) => setUsername(e.target.value)}
                onBlur={loadProfiles}
              />
            </div>
            
            <div className="form-group">
              <label>Perfil de Firefox</label>
              <select 
                value={selectedProfile} 
                onChange={(e) => setSelectedProfile(e.target.value)}
              >
                <option value="">Perfil por defecto</option>
                {profiles.map(p => (
                  <option key={p.directory_name} value={p.display_name}>
                    {p.display_name} {p.is_default && '(default)'}
                  </option>
                ))}
              </select>
            </div>
            
            <button 
              className="btn btn-primary"
              onClick={handleExtractCookies}
              disabled={extracting}
            >
              {extracting ? 'Extrayendo...' : 'Extraer Cookies'}
            </button>
          </div>
        )}

        {activeTab === 'create' && (
          <div className="card">
            <h2>Crear Cuaderno desde YouTube</h2>
            
            <div className="form-group">
              <label>URL del vídeo de YouTube</label>
              <input 
                type="text" 
                value={youtubeUrl}
                onChange={(e) => setYoutubeUrl(e.target.value)}
                placeholder="https://www.youtube.com/watch?v=..."
              />
            </div>
            
            <div className="form-group">
              <label>Idioma</label>
              <select value={language} onChange={(e) => setLanguage(e.target.value)}>
                <option value="es">Español</option>
                <option value="en">English</option>
              </select>
            </div>
            
            <div className="form-group">
              <label>Artefactos a generar:</label>
              <div className="checkbox-group">
                {ARTIFACT_TYPES.map(artifact => (
                  <div key={artifact.id} className="checkbox-item">
                    <input 
                      type="checkbox"
                      id={artifact.id}
                      checked={selectedArtifacts.includes(artifact.id)}
                      onChange={() => handleSelectArtifact(artifact.id)}
                    />
                    <label htmlFor={artifact.id}>
                      {artifact.name}
                      {artifact.limited && <span style={{ color: '#f59e0b', fontSize: '0.8em' }}> (límite)</span>}
                    </label>
                  </div>
                ))}
              </div>
            </div>
            
            <button 
              className="btn btn-primary"
              onClick={handleCreateNotebook}
              disabled={creating || !youtubeUrl}
            >
              {creating ? 'Creando...' : 'Crear Cuaderno'}
            </button>
          </div>
        )}

        {activeTab === 'notebooks' && !selectedNotebook && notebooks.length > 0 && (
          <>
            <div className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
                <h2>Mis Cuadernos</h2>
                <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
                  <input
                    type="text"
                    placeholder="Buscar cuaderno..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    style={{ padding: '8px 12px', borderRadius: '6px', border: '1px solid #ddd', width: '200px' }}
                  />
                  <select 
                    value={sortOrder} 
                    onChange={(e) => setSortOrder(e.target.value)}
                    style={{ padding: '8px 12px', borderRadius: '6px', border: '1px solid #ddd' }}
                  >
                    <option value="alpha">Alfabético (A-Z)</option>
                    <option value="alpha-rev">Alfabético (Z-A)</option>
                    <option value="date-desc">Más recientes primero</option>
                    <option value="date-asc">Más antiguos primero</option>
                  </select>
                  <button className="btn btn-secondary" onClick={loadNotebooks}>
                    Actualizar
                  </button>
                </div>
              </div>
              
              {loading ? (
                <div className="loading"><div className="spinner"></div></div>
              ) : getSortedNotebooks().length === 0 ? (
                <div className="empty-state">
                  <h3>No se encontraron cuadernos</h3>
                  <p>Prueba con otro término de búsqueda</p>
                </div>
              ) : (
                <div className="notebooks-list">
                  {getSortedNotebooks().map((notebook, index) => (
                    <div key={notebook.id} className="notebook-item">
                      <div className="notebook-info">
                        <h3><span style={{ color: '#667eea', fontWeight: 'normal' }}>#{index + 1}</span> {notebook.title}</h3>
                        <p>{notebook.url}</p>
                        {notebook.created_at && (
                          <p style={{ fontSize: '0.8rem', color: '#888' }}>
                            📅 {new Date(notebook.created_at).toLocaleDateString('es-ES', { 
                              year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' 
                            })}
                          </p>
                        )}
                      </div>
                      <div className="notebook-actions">
                        <button 
                          className="btn btn-secondary"
                          onClick={() => loadNotebookDetail(notebook.id)}
                          disabled={loadingDetail}
                        >
                          {loadingDetail ? 'Cargando...' : 'Ver Detalles'}
                        </button>
                        <a 
                          href={notebook.url} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="btn btn-primary"
                        >
                          Abrir en NotebookLM
                        </a>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}

        {activeTab === 'notebooks' && !selectedNotebook && notebooks.length === 0 && !loading && (
          <div className="card">
            <div className="empty-state">
              <h3>No hay cuadernos</h3>
              <p>Crea tu primer cuaderno desde la pestaña "Crear Cuaderno"</p>
            </div>
          </div>
        )}

        {activeTab === 'notebooks' && selectedNotebook && (
          <div className="card">
            {loadingDetail ? (
              <div className="loading">
                <div className="spinner"></div>
                <p style={{ marginTop: '16px' }}>Cargando detalles del cuaderno...</p>
              </div>
            ) : notebookDetail ? (
              <>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                  <h2>{notebookDetail.title}</h2>
                  <button className="btn btn-secondary" onClick={() => setSelectedNotebook(null)}>
                    Volver
                  </button>
                </div>
                
                <p style={{ marginBottom: '16px' }}>
                  <a href={notebookDetail.url} target="_blank" rel="noopener noreferrer">
                    {notebookDetail.url}
                  </a>
                </p>
                
                <h3>Artefactos</h3>
                <div className="artifact-grid">
                  {ARTIFACT_TYPES.map(artifact => 
                    renderArtifactCard(artifact.id, notebookDetail.artifacts?.[artifact.id], selectedNotebook)
                  )}
                </div>
                
                <div style={{ marginTop: '24px' }}>
                  <h3>Generar artefactos faltantes</h3>
                  <div className="btn-group">
                    <button 
                      className="btn btn-primary"
                      onClick={() => {
                        const faltantes = ARTIFACT_TYPES
                          .filter(a => !notebookDetail.artifacts?.[a.id]?.length)
                          .map(a => a.id)
                        handleGenerateArtifacts(selectedNotebook, faltantes)
                      }}
                      disabled={loadingDetail}
                    >
                      {loadingDetail ? 'Generando...' : 'Generar todos los faltantes'}
                    </button>
                  </div>
                </div>
              </>
            ) : (
              <div className="empty-state">
                <h3>No se pudieron cargar los detalles</h3>
                <p>Ha ocurrido un error al cargar el cuaderno. Verifica la autenticación.</p>
                <button className="btn btn-secondary" onClick={() => setSelectedNotebook(null)}>
                  Volver
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Markdown Preview Modal */}
      {showMarkdownModal && (
        <div className="modal-overlay" onClick={() => setShowMarkdownModal(null)}>
          <div className="modal-content markdown-modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{showMarkdownModal.title}</h3>
              <button className="modal-close" onClick={() => setShowMarkdownModal(null)}>×</button>
            </div>
            <div className="modal-body markdown-content">
              <ReactMarkdown>{showMarkdownModal.content}</ReactMarkdown>
            </div>
            <div className="modal-footer">
              <button 
                className="btn btn-secondary" 
                onClick={() => setShowMarkdownModal(null)}
              >
                Cerrar
              </button>
              <button 
                className="btn btn-primary"
                onClick={() => handleCopyMarkdown(showMarkdownModal.content, 'modal')}
              >
                {copiedId === 'modal' ? '✓ Copiado' : '📋 Copiar Markdown'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default App
