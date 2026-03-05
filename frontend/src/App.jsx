import { useState, useEffect } from 'react'
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
  
  // Create notebook form
  const [youtubeUrl, setYoutubeUrl] = useState('')
  const [language, setLanguage] = useState('es')
  const [selectedArtifacts, setSelectedArtifacts] = useState(DEFAULT_ARTIFACTS)
  const [creating, setCreating] = useState(false)
  
  // Notebook detail
  const [selectedNotebook, setSelectedNotebook] = useState(null)
  const [notebookDetail, setNotebookDetail] = useState(null)
  const [loadingDetail, setLoadingDetail] = useState(false)
  
  // Auth form
  const [username, setUsername] = useState('oscar')
  const [selectedProfile, setSelectedProfile] = useState('')
  const [profiles, setProfiles] = useState([])
  const [extracting, setExtracting] = useState(false)

  useEffect(() => {
    checkAuthStatus()
    loadProfiles()
  }, [])

  useEffect(() => {
    if (activeTab === 'notebooks') {
      loadNotebooks()
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
    try {
      const data = await api.getNotebooks()
      setNotebooks(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const loadNotebookDetail = async (notebookId) => {
    setLoadingDetail(true)
    setError(null)
    try {
      const data = await api.getNotebook(notebookId, language)
      setNotebookDetail(data)
      setSelectedNotebook(notebookId)
    } catch (err) {
      setError(err.message)
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
      loadNotebookDetail(notebookId)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoadingDetail(false)
    }
  }

  const handleSelectArtifact = (artifactId) => {
    setSelectedArtifacts(prev => 
      prev.includes(artifactId)
        ? prev.filter(a => a !== artifactId)
        : [...prev, artifactId]
    )
  }

  const renderArtifactCard = (artifact, artifactList, notebookId) => {
    const isAvailable = artifactList && artifactList.length > 0
    const artifactInfo = ARTIFACT_TYPES.find(a => a.id === artifact)
    
    return (
      <div key={artifact} className={`artifact-card ${isAvailable ? 'available' : 'not-available'}`}>
        <h4>{artifactInfo?.name || artifact}</h4>
        <p className={`status ${isAvailable ? 'available' : 'not-available'}`}>
          {isAvailable ? '✓ Disponible' : '✗ No disponible'}
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
        {isAvailable && artifactList[0]?.download_url && (
          <a 
            href={artifactList[0].download_url} 
            target="_blank" 
            rel="noopener noreferrer"
            className="btn btn-primary"
            style={{ display: 'inline-block', marginTop: '8px', textDecoration: 'none' }}
          >
            Descargar
          </a>
        )}
      </div>
    )
  }

  return (
    <div>
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
            onClick={() => { setActiveTab('auth'); setError(null); setSuccess(null); }}
          >
            Autenticación
          </button>
        </div>

        {error && <div className="alert alert-error">{error}</div>}
        {success && <div className="alert alert-success">{success}</div>}

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
              disabled={extracting || !authStatus?.authenticated}
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

        {activeTab === 'notebooks' && !selectedNotebook && (
          <>
            <div className="card">
              <h2>Mis Cuadernos</h2>
              <button className="btn btn-secondary" onClick={loadNotebooks} style={{ marginBottom: '16px' }}>
                Actualizar
              </button>
              
              {loading ? (
                <div className="loading"><div className="spinner"></div></div>
              ) : notebooks.length === 0 ? (
                <div className="empty-state">
                  <h3>No hay cuadernos</h3>
                  <p>Crea tu primer cuaderno desde la pestaña "Crear Cuaderno"</p>
                </div>
              ) : (
                <div className="notebooks-list">
                  {notebooks.map(notebook => (
                    <div key={notebook.id} className="notebook-item">
                      <div className="notebook-info">
                        <h3>{notebook.title}</h3>
                        <p>{notebook.url}</p>
                      </div>
                      <div className="notebook-actions">
                        <button 
                          className="btn btn-secondary"
                          onClick={() => loadNotebookDetail(notebook.id)}
                        >
                          Ver Detalles
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

        {activeTab === 'notebooks' && selectedNotebook && notebookDetail && (
          <div className="card">
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
          </div>
        )}
      </div>
    </div>
  )
}

export default App
