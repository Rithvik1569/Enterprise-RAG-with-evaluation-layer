import { useState, useEffect, useCallback, useRef } from 'react';
import { Routes, Route, Link, useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import AuthPage from './components/AuthPage';

export default function App() {
  const [token, setToken] = useState(() => localStorage.getItem('rag_token'));
  const [user, setUser] = useState(null);
  const [backendStatus, setBackendStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const navigate = useNavigate();
  const location = useLocation();

  // Core features state
  const [documents, setDocuments] = useState([]);
  const [loadingDocs, setLoadingDocs] = useState(false);
  const [chatHistory, setChatHistory] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [selectedDocId, setSelectedDocId] = useState('');
  const [fileToUpload, setFileToUpload] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [expandedCitationIndex, setExpandedCitationIndex] = useState(null);

  // Admin Analytics state
  const [analyticsData, setAnalyticsData] = useState(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [analyticsError, setAnalyticsError] = useState(null);

  const messagesEndRef = useRef(null);

  // Scroll to bottom on new messages
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (location.pathname === '/') {
      scrollToBottom();
    }
  }, [chatHistory, chatLoading, location.pathname]);

  // ------------------------------------------------------------------
  // On mount — rehydrate user from stored token
  // ------------------------------------------------------------------
  const [appError, setAppError] = useState(null);

  useEffect(() => {
    let isMounted = true;

    const initializeApp = async () => {
      if (!isMounted) return;

      // 2. Once backend is up, check auth if token exists
      const stored = localStorage.getItem('rag_token');
      if (!stored) {
        setLoading(false);
        return;
      }

      try {
        const r = await axios.get('/api/auth/me', {
          headers: { Authorization: `Bearer ${stored}` },
        });
        setToken(stored);
        setUser(r.data);
      } catch (err) {
        // Only log out if it's explicitly an unauthorized error (401), not network error.
        if (err.response && err.response.status === 401) {
          localStorage.removeItem('rag_token');
          setToken(null);
          setUser(null);
        } else {
          // If backend is still starting, keep the token and let them into the UI instantly.
          setToken(stored);
          setUser({ username: 'Loading...', role: 'user' });
        }
      } finally {
        setLoading(false);
      }
    };

    initializeApp();

    return () => { isMounted = false; };
  }, []);

  // ------------------------------------------------------------------
  // Poll health endpoint and fetch documents list when authenticated
  // ------------------------------------------------------------------
  const fetchDocuments = useCallback(async () => {
    if (!token) return;
    setLoadingDocs(true);
    try {
      const res = await axios.get('/api/documents', {
        headers: { Authorization: `Bearer ${token}` },
      });
      setDocuments(res.data);
    } catch (err) {
      console.error('Failed to fetch documents:', err);
    } finally {
      setLoadingDocs(false);
    }
  }, [token]);

  // Fetch Analytics data
  const fetchAnalytics = useCallback(async () => {
    if (!token) return;
    setAnalyticsLoading(true);
    setAnalyticsError(null);
    try {
      const res = await axios.get('/api/admin/analytics', {
        headers: { Authorization: `Bearer ${token}` },
      });
      setAnalyticsData(res.data);
    } catch (err) {
      setAnalyticsError(err.response?.data?.detail || err.message || 'Error loading analytics');
    } finally {
      setAnalyticsLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (!token) return;

    const fetchStatus = async () => {
      try {
        setError(null);
        const response = await axios.get('/api/health');
        setBackendStatus(response.data);
      } catch (err) {
        const msg = err.message || 'Unknown error';
        setError(msg);
        setBackendStatus(null);
      }
    };

    fetchStatus();
    fetchDocuments();
    const interval = setInterval(fetchStatus, 15000);
    return () => clearInterval(interval);
  }, [token, fetchDocuments]);

  // ------------------------------------------------------------------
  // Handlers
  // ------------------------------------------------------------------
  const handleAuthSuccess = useCallback((newToken, userInfo) => {
    setToken(newToken);
    setUser(userInfo);
  }, []);

  const handleLogout = useCallback(() => {
    localStorage.removeItem('rag_token');
    setToken(null);
    setUser(null);
    setBackendStatus(null);
    setDocuments([]);
    setChatHistory([]);
    navigate('/');
  }, [navigate]);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      setFileToUpload(e.target.files[0]);
      setUploadError(null);
      setUploadSuccess(false);
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!fileToUpload || !token) return;

    setUploading(true);
    setUploadError(null);
    setUploadSuccess(false);

    const formData = new FormData();
    formData.append('file', fileToUpload);
    formData.append('chunk_size', '1000');
    formData.append('chunk_overlap', '200');

    try {
      await axios.post('/api/documents/upload', formData, {
        headers: { 
          Authorization: `Bearer ${token}`,
          'Content-Type': 'multipart/form-data'
        },
      });

      setUploadSuccess(true);
      setFileToUpload(null);
      // Reset input element
      const fileInput = document.getElementById('doc-file-input');
      if (fileInput) fileInput.value = '';
      
      // Refresh documents list
      await fetchDocuments();
    } catch (err) {
      setUploadError(err.response?.data?.detail || err.message || 'An error occurred during upload');
    } finally {
      setUploading(false);
    }
  };

  const handleDeleteDoc = async (id) => {
    if (!token) return;
    if (!confirm('Are you sure you want to delete this document? All associated vector chunks will be permanently removed.')) return;

    try {
      await axios.delete(`/api/documents/${id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      await fetchDocuments();
      if (selectedDocId === id) {
        setSelectedDocId('');
      }
    } catch (err) {
      console.error(err);
      alert('An error occurred during deletion.');
    }
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!chatInput.trim() || chatLoading || !token) return;

    const userMsgText = chatInput.trim();
    setChatInput('');
    setChatLoading(true);

    // Append user message to logs
    const newHistory = [...chatHistory, { sender: 'user', text: userMsgText }];
    setChatHistory(newHistory);

    try {
      const res = await axios.post('/api/chat', {
        message: userMsgText,
        document_id: selectedDocId || null,
        top_k: 4,
      }, {
        headers: { Authorization: `Bearer ${token}` },
      });

      const data = res.data;
      setChatHistory([
        ...newHistory,
        {
          sender: 'assistant',
          text: data.answer,
          responseTime: data.response_time,
          citations: data.citations,
          evaluation: data.evaluation,
        },
      ]);
    } catch (err) {
      setChatHistory([
        ...newHistory,
        {
          sender: 'assistant',
          text: '❌ Failed to reach RAG Assistant. Please check if backend is online.',
        },
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  // Helper to draw an SVG sparkline for daily metrics
  const drawSparkline = (dataList, key, width = 320, height = 120) => {
    if (!dataList || dataList.length < 2) return null;
    
    const padding = 15;
    const values = dataList.map(d => Number(d[key]));
    const maxVal = Math.max(...values, 0.1);
    const minVal = Math.min(...values, 0);

    const range = maxVal - minVal;
    
    // Construct coordinates
    const points = dataList.map((d, i) => {
      const x = padding + (i / (dataList.length - 1)) * (width - 2 * padding);
      const val = Number(d[key]);
      const y = height - padding - ((val - minVal) / range) * (height - 2 * padding);
      return { x, y, date: d.date, val };
    });

    const pathData = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');
    
    // Construct fill path
    const fillPathData = `${pathData} L ${points[points.length - 1].x} ${height - padding} L ${points[0].x} ${height - padding} Z`;

    return { points, pathData, fillPathData };
  };

  // ------------------------------------------------------------------
  // Gate: Error state, Loading state, or Auth page
  // ------------------------------------------------------------------
  if (appError) {
    return (
      <div className="min-h-screen bg-[#0b0c10] flex items-center justify-center text-slate-400 font-sans p-6">
        <div className="max-w-md w-full bg-slate-900/50 border border-slate-800/80 rounded-2xl p-8 shadow-2xl backdrop-blur-sm text-center space-y-6">
          <div className="mx-auto w-16 h-16 bg-rose-500/10 border border-rose-500/20 rounded-full flex items-center justify-center text-rose-500 text-3xl shadow-inner shadow-rose-500/20">
            {appError.type === 'critical' ? '⚠️' : '🔌'}
          </div>
          <div className="space-y-2">
            <h2 className="text-xl font-bold text-slate-100 tracking-tight">{appError.title}</h2>
            <p className="text-sm text-slate-400 leading-relaxed">
              {appError.message}
            </p>
          </div>
          <button 
            onClick={() => window.location.reload()} 
            className="w-full bg-slate-800 hover:bg-slate-700 text-white font-semibold py-3 px-4 rounded-xl text-sm transition active:scale-[0.98] border border-slate-700/50 hover:border-slate-600/50 shadow-lg cursor-pointer"
          >
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0b0c10] flex items-center justify-center text-slate-400 font-medium">
        <div className="flex flex-col items-center gap-3">
          <svg className="animate-spin h-8 w-8 text-violet-500" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span className="text-sm tracking-wider uppercase">Loading RAG Interface...</span>
        </div>
      </div>
    );
  }

  if (!token || !user) {
    return <AuthPage onAuthSuccess={handleAuthSuccess} />;
  }

  const roleLabel = user.role === 'admin' ? '🛡 Admin' : '👤 User';
  const roleClass = user.role === 'admin' 
    ? 'bg-violet-500/10 text-violet-400 border border-violet-500/20' 
    : 'bg-slate-800 text-slate-400 border border-slate-700/50';

  // ------------------------------------------------------------------
  // Dashboard Layout
  // ------------------------------------------------------------------
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#0b0c10] text-slate-100 font-sans">
      
      {/* Sidebar */}
      <aside className="w-80 flex flex-col bg-slate-950/80 border-r border-slate-900/60 backdrop-blur-md shrink-0">
        
        {/* Brand Header */}
        <div className="flex items-center gap-3 px-6 py-5 border-b border-slate-900/50">
          <div className="flex items-center justify-center w-8 h-8 bg-gradient-to-tr from-violet-600 to-cyan-500 rounded-lg text-white font-bold text-sm shadow-md shadow-violet-600/10">
            ▲
          </div>
          <div>
            <h2 className="font-bold text-base tracking-tight bg-gradient-to-r from-white to-slate-300 bg-clip-text text-transparent">
              Enterprise RAG
            </h2>
            <p className="text-[10px] text-slate-500 font-semibold tracking-wider uppercase">RAG Engine v0.5</p>
          </div>
        </div>

        {/* View Selection Navigation */}
        <nav className="px-4 py-4 space-y-1 border-b border-slate-900/40">
          <Link
            to="/"
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-bold transition cursor-pointer ${
              location.pathname === '/' 
                ? 'bg-violet-600/10 text-violet-400 border border-violet-500/20' 
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/30'
            }`}
          >
            <span>💬</span>
            <span>RAG Grounded Chat</span>
          </Link>
          
          {user.role === 'admin' && (
            <Link
              to="/analytics"
              onClick={() => {
                if (location.pathname !== '/analytics') fetchAnalytics();
              }}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-bold transition cursor-pointer ${
                location.pathname === '/analytics' 
                  ? 'bg-violet-600/10 text-violet-400 border border-violet-500/20' 
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/30'
              }`}
            >
              <span>📊</span>
              <span>Analytics Dashboard</span>
            </Link>
          )}
        </nav>

        {/* Action Controls/Ingestion list: Always visible and scrollable in sidebar */}
        <div className="flex-1 overflow-y-auto px-4 py-5 space-y-6">
          
          {/* Document Ingester */}
          <div className="bg-slate-900/40 border border-slate-800/80 rounded-xl p-4 space-y-4">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
              <span>📤</span> Document Ingestion
            </h3>
            
            <form onSubmit={handleUpload} className="space-y-3">
              <div className="border-2 border-dashed border-slate-800 hover:border-violet-600/50 hover:bg-slate-950/30 rounded-lg p-5 text-center cursor-pointer transition duration-300">
                <input
                  type="file"
                  id="doc-file-input"
                  accept=".pdf,.txt,.docx,.md"
                  onChange={handleFileChange}
                  className="hidden"
                />
                <label htmlFor="doc-file-input" className="cursor-pointer block space-y-2">
                  <span className="text-2xl block">📄</span>
                  {fileToUpload ? (
                    <span className="text-xs font-semibold text-violet-400 block break-all px-1">
                      {fileToUpload.name}
                    </span>
                  ) : (
                    <span className="text-xs text-slate-500 block">
                      Select PDF, TXT, MD, DOCX
                    </span>
                  )}
                </label>
              </div>
              
              <button
                type="submit"
                className="w-full bg-slate-800 hover:bg-slate-700 text-white font-semibold py-2 px-3 rounded-lg text-xs transition active:scale-[0.98] disabled:opacity-50 cursor-pointer flex items-center justify-center gap-2"
                disabled={!fileToUpload || uploading}
              >
                {uploading ? (
                  <>
                    <svg className="animate-spin h-3.5 w-3.5 text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <span>Embedding chunks...</span>
                  </>
                ) : (
                  'Ingest Document'
                )}
              </button>
            </form>

            {uploadSuccess && (
              <p className="text-[11px] text-emerald-400 font-medium flex items-center gap-1.5 bg-emerald-500/5 border border-emerald-500/10 p-2.5 rounded-lg">
                <span>✅</span> Grounded in vector store!
              </p>
            )}
            {uploadError && (
              <p className="text-[11px] text-rose-400 font-medium flex items-center gap-1.5 bg-rose-500/5 border border-rose-500/10 p-2.5 rounded-lg break-all">
                <span>❌</span> {uploadError}
              </p>
            )}
          </div>

          {/* Ingested Document List */}
          <div className="space-y-3">
            <div className="flex justify-between items-center px-1">
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                <span>📚</span> Knowledge Base ({documents.length})
              </h3>
              <button 
                onClick={fetchDocuments}
                className="text-[10px] text-slate-500 hover:text-slate-300 transition cursor-pointer"
                title="Refresh Documents"
              >
                🔄
              </button>
            </div>

            <div className="space-y-2 max-h-[220px] overflow-y-auto pr-1">
              {loadingDocs ? (
                <p className="text-xs text-slate-600 italic pl-1">Syncing index...</p>
              ) : documents.length === 0 ? (
                <p className="text-xs text-slate-600 pl-1">No documents uploaded yet.</p>
              ) : (
                documents.map((doc) => (
                  <div
                    key={doc.id}
                    className="group flex items-center justify-between p-3 bg-slate-900/30 hover:bg-slate-900/60 border border-slate-900/80 hover:border-slate-800/80 rounded-xl transition duration-200"
                  >
                    <div className="min-w-0 flex-1 pr-2 space-y-1">
                      <p className="text-xs font-semibold text-slate-200 truncate" title={doc.filename}>
                        {doc.filename}
                      </p>
                      <div className="flex items-center gap-2 text-[10px] text-slate-500">
                        <span>{(doc.size / 1024).toFixed(0)} KB</span>
                        <span>•</span>
                        <span className={`capitalize font-bold ${
                          doc.processing_status === 'processed' ? 'text-emerald-500/80' : doc.processing_status === 'failed' ? 'text-rose-500/80' : 'text-amber-500/80'
                        }`}>
                          {doc.processing_status} ({doc.chunk_count})
                        </span>
                      </div>
                    </div>
                    
                    <button
                      onClick={() => handleDeleteDoc(doc.id)}
                      className="opacity-0 group-hover:opacity-100 hover:bg-rose-500/10 text-rose-500 p-1.5 rounded-lg border border-transparent hover:border-rose-500/20 transition cursor-pointer shrink-0"
                      title="Delete document"
                    >
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Footer info & connection indicator */}
        <div className="p-4 border-t border-slate-900/50 bg-slate-950/60 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="w-8 h-8 rounded-full bg-violet-600/20 border border-violet-500/30 text-violet-400 font-bold text-xs flex items-center justify-center uppercase shrink-0">
                {user.username.slice(0, 2)}
              </div>
              <div className="min-w-0 leading-tight">
                <p className="text-xs font-bold text-slate-200 truncate">{user.username}</p>
                <span className={`inline-block px-1.5 py-0.5 rounded text-[8px] font-bold uppercase tracking-wider mt-0.5 scale-90 -translate-x-1 origin-left border ${roleClass}`}>
                  {roleLabel}
                </span>
              </div>
            </div>
            
            <button
              onClick={handleLogout}
              className="hover:bg-slate-800 text-slate-400 hover:text-slate-200 p-1.5 rounded-lg border border-slate-900 transition cursor-pointer"
              title="Sign Out"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
              </svg>
            </button>
          </div>

          <div className="flex flex-col gap-1.5 bg-slate-900/40 p-2.5 rounded-xl border border-slate-900/80">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${backendStatus ? 'bg-emerald-500 shadow-sm shadow-emerald-500/50' : 'bg-rose-500'}`} />
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                  {backendStatus ? 'Connected' : 'Offline'}
                </span>
              </div>
              {backendStatus && (
                <span className="text-[9px] text-slate-500 font-semibold">
                  FastAPI v{backendStatus.version || '0.2'}
                </span>
              )}
            </div>
            {error && (
              <p className="text-[9px] text-rose-400 font-medium">
                {error}
              </p>
            )}
          </div>
        </div>
      </aside>

      {/* Main Workspace content */}
      <div className="flex-1 flex flex-col min-w-0">
        
        <Routes>
          {/* Chat view */}
          <Route path="/" element={
          <>
            <header className="h-16 px-6 border-b border-slate-900/60 bg-slate-950/30 flex items-center justify-between shrink-0">
              <div className="flex items-center gap-3">
                <h1 className="font-bold text-base tracking-tight text-white">RAG Grounded Console</h1>
                <span className="px-2 py-0.5 bg-violet-600/10 text-violet-400 border border-violet-500/10 rounded-full text-[10px] font-semibold">
                  Live Evaluation Layer
                </span>
              </div>

              <div className="flex items-center gap-2 text-xs">
                <span className="text-slate-500 font-medium">Grounding context:</span>
                <select
                  value={selectedDocId}
                  onChange={(e) => setSelectedDocId(e.target.value)}
                  className="bg-slate-900/80 border border-slate-800/80 hover:border-slate-700 text-slate-200 text-xs px-3 py-1.5 rounded-lg outline-none cursor-pointer focus:ring-1 focus:ring-violet-500/50 transition"
                >
                  <option value="">🔍 Search All Ingested Knowledge</option>
                  {documents.filter(d => d.processing_status === 'processed').map((doc) => (
                    <option key={doc.id} value={doc.id}>
                      📄 {doc.filename.slice(0, 30)}{doc.filename.length > 30 ? '...' : ''}
                    </option>
                  ))}
                </select>
              </div>
            </header>

            <div className="flex-1 overflow-y-auto px-6 py-8 space-y-6">
              <div className="max-w-3xl mx-auto space-y-6">
                
                {/* Welcome message */}
                <div className="flex items-start gap-4">
                  <div className="w-8 h-8 rounded-full bg-violet-600/10 border border-violet-500/20 text-violet-400 font-bold text-xs flex items-center justify-center uppercase shrink-0">
                    AI
                  </div>
                  <div className="bg-slate-900/20 border border-slate-900/80 rounded-2xl rounded-tl-none p-4 max-w-xl shadow-sm text-sm text-slate-300 leading-relaxed">
                    <p className="font-bold text-slate-100 mb-1 font-display">Welcome, {user.username}!</p>
                    Ask me any question. I will locate the matching source snippets in your knowledge base, run an evaluation layer on my answer to inspect hallucinations/relevance, and deliver the final response.
                  </div>
                </div>

                {chatHistory.map((msg, index) => (
                  <div 
                    key={index} 
                    className={`flex items-start gap-4 ${msg.sender === 'user' ? 'flex-row-reverse' : ''}`}
                  >
                    <div className={`w-8 h-8 rounded-full font-bold text-xs flex items-center justify-center uppercase shrink-0 border ${
                      msg.sender === 'user' 
                        ? 'bg-cyan-600/20 border-cyan-500/30 text-cyan-400' 
                        : 'bg-violet-600/20 border-violet-500/30 text-violet-400'
                    }`}>
                      {msg.sender === 'user' ? user.username.slice(0, 2) : 'AI'}
                    </div>

                    <div className="flex flex-col max-w-2xl space-y-2">
                      <div className={`text-sm rounded-2xl p-4 shadow-sm leading-relaxed border ${
                        msg.sender === 'user' 
                          ? 'bg-slate-900/60 border-slate-800 text-slate-100 rounded-tr-none' 
                          : 'bg-slate-950/30 border-slate-900/80 text-slate-200 rounded-tl-none'
                      }`}>
                        <div className="white-space-pre-wrap font-medium">
                          {msg.text}
                        </div>

                        {msg.sender === 'assistant' && (
                          <div className="mt-4 pt-3.5 border-t border-slate-900/80 space-y-4 text-[11px] text-slate-500">
                            <div className="flex items-center justify-between text-slate-500 font-semibold px-0.5">
                              {msg.responseTime !== undefined && (
                                <span>⏱ Generation: <strong>{msg.responseTime}s</strong></span>
                              )}
                              {msg.citations && msg.citations.length > 0 && (
                                <span>📚 Grounding: <strong>{msg.citations.length} sources</strong></span>
                              )}
                            </div>

                            {msg.evaluation && (
                              <div className="bg-slate-900/30 border border-slate-900 rounded-xl p-3.5 space-y-3.5">
                                <div className="flex items-center justify-between font-bold text-slate-300">
                                  <span className="flex items-center gap-1 text-[11px] uppercase tracking-wider">
                                    📊 DeepEval RAG layer
                                  </span>
                                  <span className="font-semibold text-[10px] text-slate-500">
                                    Eval Latency: {msg.evaluation.latency_ms} ms
                                  </span>
                                </div>

                                <div className="grid grid-cols-2 gap-x-5 gap-y-3">
                                  {/* 1. Faithfulness */}
                                  <div className="space-y-1">
                                    <div className="flex justify-between font-medium">
                                      <span>Faithfulness</span>
                                      <span className={`font-bold ${
                                        msg.evaluation.faithfulness >= 0.8 ? 'text-emerald-400' : msg.evaluation.faithfulness >= 0.5 ? 'text-amber-400' : 'text-rose-400'
                                      }`}>
                                        {(msg.evaluation.faithfulness * 100).toFixed(2)}%
                                      </span>
                                    </div>
                                    <div className="h-1 bg-slate-950 rounded-full overflow-hidden">
                                      <div 
                                        className={`h-full rounded-full transition-all duration-500 ${
                                          msg.evaluation.faithfulness >= 0.8 ? 'bg-emerald-500' : msg.evaluation.faithfulness >= 0.5 ? 'bg-amber-500' : 'bg-rose-500'
                                        }`}
                                        style={{ width: `${msg.evaluation.faithfulness * 100}%` }}
                                      />
                                    </div>
                                  </div>

                                  {/* 2. Answer Relevance */}
                                  <div className="space-y-1">
                                    <div className="flex justify-between font-medium">
                                      <span>Answer Relevance</span>
                                      <span className={`font-bold ${
                                        msg.evaluation.answer_relevance >= 0.8 ? 'text-emerald-400' : msg.evaluation.answer_relevance >= 0.5 ? 'text-amber-400' : 'text-rose-400'
                                      }`}>
                                        {(msg.evaluation.answer_relevance * 100).toFixed(2)}%
                                      </span>
                                    </div>
                                    <div className="h-1 bg-slate-950 rounded-full overflow-hidden">
                                      <div 
                                        className={`h-full rounded-full transition-all duration-500 ${
                                          msg.evaluation.answer_relevance >= 0.8 ? 'bg-emerald-500' : msg.evaluation.answer_relevance >= 0.5 ? 'bg-amber-500' : 'bg-rose-500'
                                        }`}
                                        style={{ width: `${msg.evaluation.answer_relevance * 100}%` }}
                                      />
                                    </div>
                                  </div>

                                  {/* 3. Context Precision */}
                                  <div className="space-y-1">
                                    <div className="flex justify-between font-medium">
                                      <span>Context Precision</span>
                                      <span className={`font-bold ${
                                        msg.evaluation.context_precision >= 0.8 ? 'text-emerald-400' : msg.evaluation.context_precision >= 0.5 ? 'text-amber-400' : 'text-rose-400'
                                      }`}>
                                        {(msg.evaluation.context_precision * 100).toFixed(2)}%
                                      </span>
                                    </div>
                                    <div className="h-1 bg-slate-950 rounded-full overflow-hidden">
                                      <div 
                                        className={`h-full rounded-full transition-all duration-500 ${
                                          msg.evaluation.context_precision >= 0.8 ? 'bg-emerald-500' : msg.evaluation.context_precision >= 0.5 ? 'bg-amber-500' : 'bg-rose-500'
                                        }`}
                                        style={{ width: `${msg.evaluation.context_precision * 100}%` }}
                                      />
                                    </div>
                                  </div>

                                  {/* 4. Context Recall */}
                                  <div className="space-y-1">
                                    <div className="flex justify-between font-medium">
                                      <span>Context Recall</span>
                                      <span className={`font-bold ${
                                        msg.evaluation.context_recall >= 0.8 ? 'text-emerald-400' : msg.evaluation.context_recall >= 0.5 ? 'text-amber-400' : 'text-rose-400'
                                      }`}>
                                        {(msg.evaluation.context_recall * 100).toFixed(2)}%
                                      </span>
                                    </div>
                                    <div className="h-1 bg-slate-950 rounded-full overflow-hidden">
                                      <div 
                                        className={`h-full rounded-full transition-all duration-500 ${
                                          msg.evaluation.context_recall >= 0.8 ? 'bg-emerald-500' : msg.evaluation.context_recall >= 0.5 ? 'bg-amber-500' : 'bg-rose-500'
                                        }`}
                                        style={{ width: `${msg.evaluation.context_recall * 100}%` }}
                                      />
                                    </div>
                                  </div>
                                </div>
                              </div>
                            )}

                            {msg.citations && msg.citations.length > 0 && (
                              <div className="space-y-2">
                                {msg.citations.map((cite, cIdx) => {
                                  const key = `${index}-${cIdx}`;
                                  const isExpanded = expandedCitationIndex === key;
                                  return (
                                    <div
                                      key={key}
                                      className="bg-slate-950/40 border border-slate-900 rounded-lg overflow-hidden transition"
                                    >
                                      <button
                                        onClick={() => setExpandedCitationIndex(isExpanded ? null : key)}
                                        className="w-full text-left px-3 py-2 bg-slate-950/20 hover:bg-slate-900/30 flex items-center justify-between text-[11px] font-semibold text-slate-400 cursor-pointer"
                                      >
                                        <span className="truncate text-violet-400">
                                          [{cIdx + 1}] {cite.filename} (Chunk {cite.chunk_index})
                                        </span>
                                        <span className="text-[10px] text-slate-500 shrink-0 ml-2">
                                          Score: {cite.score.toFixed(3)} {isExpanded ? '▲' : '▼'}
                                        </span>
                                      </button>
                                      {isExpanded && (
                                        <div className="p-3 bg-slate-950/80 border-t border-slate-900 text-slate-300 font-mono text-[11px] leading-relaxed max-h-40 overflow-y-auto whitespace-pre-wrap select-text">
                                          {cite.text}
                                        </div>
                                      )}
                                    </div>
                                  );
                                })}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}

                {chatLoading && (
                  <div className="flex items-start gap-4">
                    <div className="w-8 h-8 rounded-full bg-violet-600/10 border border-violet-500/20 text-violet-400 font-bold text-xs flex items-center justify-center uppercase shrink-0">
                      AI
                    </div>
                    <div className="bg-slate-900/20 border border-slate-900/80 border-dashed rounded-2xl rounded-tl-none p-4 max-w-xl text-sm text-slate-500 flex items-center gap-2">
                      <svg className="animate-spin h-4 w-4 text-violet-500" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      <span>Searching documents and calculating RAG metrics...</span>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>
            </div>

            <div className="p-6 border-t border-slate-900/50 bg-[#0b0c10] shrink-0">
              <div className="max-w-3xl mx-auto">
                <form onSubmit={handleSendMessage} className="relative flex items-center">
                  <input
                    type="text"
                    className="w-full bg-slate-950/60 border border-slate-800 focus:border-violet-500 text-slate-100 placeholder-slate-600 rounded-2xl pl-4 pr-16 py-3.5 text-sm focus:outline-none focus:ring-4 focus:ring-violet-500/10 transition leading-normal"
                    placeholder={chatLoading ? 'Reasoning in progress...' : 'Ask RAG Assistant... (e.g., Explain the core concepts)'}
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    disabled={chatLoading}
                    autoComplete="off"
                  />
                  <button
                    type="submit"
                    className="absolute right-2 px-4 py-2 bg-gradient-to-r from-violet-600 to-cyan-500 hover:from-violet-700 hover:to-cyan-600 text-white font-bold rounded-xl text-xs shadow-lg shadow-violet-600/10 hover:shadow-violet-600/20 active:scale-[0.98] transition cursor-pointer"
                    disabled={chatLoading || !chatInput.trim()}
                  >
                    Send
                  </button>
                </form>
                <p className="text-[10px] text-slate-600 text-center mt-2.5">
                  Powered by Enterprise RAG Evaluation Platform. All queries undergo automated faithfulness check.
                </p>
              </div>
            </div>
          </>
          } />

          {/* Admin Analytics view */}
          <Route path="/analytics" element={
          <>
            <header className="h-16 px-6 border-b border-slate-900/60 bg-slate-950/30 flex items-center justify-between shrink-0">
              <div className="flex items-center gap-3">
                <h1 className="font-bold text-base tracking-tight text-white font-display">System Analytics</h1>
                <span className="px-2 py-0.5 bg-cyan-600/10 text-cyan-400 border border-cyan-500/10 rounded-full text-[10px] font-semibold">
                  Administrator Console
                </span>
              </div>
              <button 
                onClick={fetchAnalytics}
                className="bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 text-xs px-3.5 py-1.5 rounded-lg font-semibold active:scale-[0.98] transition cursor-pointer"
              >
                🔄 Refresh Stats
              </button>
            </header>

            <div className="flex-1 overflow-y-auto px-8 py-8 space-y-8 bg-[#0b0c10]">
              {analyticsLoading && (
                <div className="flex justify-center py-20 text-slate-400">
                  <div className="flex flex-col items-center gap-3">
                    <svg className="animate-spin h-6 w-6 text-cyan-400" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <span className="text-xs uppercase tracking-wider">Gathering system metrics...</span>
                  </div>
                </div>
              )}

              {analyticsError && (
                <div className="max-w-3xl mx-auto p-4 bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm rounded-xl">
                  ⚠️ <strong>Failed to load analytics:</strong> {analyticsError}
                </div>
              )}

              {!analyticsLoading && !analyticsError && analyticsData && (
                <div className="max-w-5xl mx-auto space-y-8">
                  
                  {/* Summary Cards */}
                  <div className="grid grid-cols-4 gap-4">
                    
                    {/* total requests */}
                    <div className="bg-slate-950/60 border border-slate-900 p-5 rounded-2xl space-y-1">
                      <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Total Requests</p>
                      <p className="text-3xl font-bold font-display text-white">{analyticsData.summary.total_requests}</p>
                      <p className="text-[10px] text-slate-600">Evaluations recorded</p>
                    </div>

                    {/* average faithfulness */}
                    <div className="bg-slate-950/60 border border-slate-900 p-5 rounded-2xl space-y-1">
                      <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Faithfulness</p>
                      <p className="text-3xl font-bold font-display text-emerald-400">
                        {(analyticsData.summary.avg_faithfulness * 100).toFixed(1)}%
                      </p>
                      <p className="text-[10px] text-slate-600">Avg grounding accuracy</p>
                    </div>

                    {/* hallucination rate */}
                    <div className="bg-slate-950/60 border border-slate-900 p-5 rounded-2xl space-y-1">
                      <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Hallucination Rate</p>
                      <p className="text-3xl font-bold font-display text-rose-400">
                        {(analyticsData.summary.hallucination_rate * 100).toFixed(1)}%
                      </p>
                      <p className="text-[10px] text-slate-600">Faithfulness &lt; 80%</p>
                    </div>

                    {/* average latency */}
                    <div className="bg-slate-950/60 border border-slate-900 p-5 rounded-2xl space-y-1">
                      <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Avg Latency</p>
                      <p className="text-3xl font-bold font-display text-cyan-400">
                        {analyticsData.summary.avg_latency_ms.toFixed(0)} <span className="text-sm font-semibold text-slate-500">ms</span>
                      </p>
                      <p className="text-[10px] text-slate-600">Evaluation processing delay</p>
                    </div>
                  </div>

                  {/* SVG Charts */}
                  <div className="grid grid-cols-2 gap-6">
                    
                    {/* Latency over time */}
                    <div className="bg-slate-950/40 border border-slate-900 p-6 rounded-2xl space-y-4">
                      <div>
                        <h3 className="text-sm font-bold text-slate-300 font-display">Evaluation Latency Trend (ms)</h3>
                        <p className="text-[10px] text-slate-500">Mean processing duration by calendar date</p>
                      </div>
                      
                      <div className="h-44 w-full flex items-center justify-center bg-slate-950/60 border border-slate-900/60 rounded-xl relative overflow-hidden">
                        {analyticsData.daily_stats && analyticsData.daily_stats.length >= 2 ? (
                          (() => {
                            const chart = drawSparkline(analyticsData.daily_stats, 'avg_latency_ms', 400, 160);
                            if (!chart) return null;
                            return (
                              <svg className="w-full h-full" viewBox="0 0 400 160">
                                <defs>
                                  <linearGradient id="latencyGlow" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.15" />
                                    <stop offset="100%" stopColor="#06b6d4" stopOpacity="0" />
                                  </linearGradient>
                                </defs>
                                {/* Gridline */}
                                <line x1="15" y1="80" x2="385" y2="80" stroke="rgba(255,255,255,0.03)" strokeDasharray="3,3" />
                                {/* Area */}
                                <path d={chart.fillPathData} fill="url(#latencyGlow)" />
                                {/* Line */}
                                <path d={chart.pathData} fill="none" stroke="#06b6d4" strokeWidth="2.5" />
                                {/* Nodes */}
                                {chart.points.map((p, i) => (
                                  <g key={i}>
                                    <circle cx={p.x} cy={p.y} r="3" fill="#06b6d4" />
                                    {/* Text Date for first/last */}
                                    {(i === 0 || i === chart.points.length - 1) && (
                                      <text x={p.x} y={150} fill="#6b7280" fontSize="7" textAnchor={i === 0 ? 'start' : 'end'}>
                                        {p.date.slice(5)}
                                      </text>
                                    )}
                                  </g>
                                ))}
                              </svg>
                            );
                          })()
                        ) : (
                          <span className="text-xs text-slate-600 italic">Not enough historical daily records to graph.</span>
                        )}
                      </div>
                    </div>

                    {/* Faithfulness vs Hallucination Rate */}
                    <div className="bg-slate-950/40 border border-slate-900 p-6 rounded-2xl space-y-4">
                      <div>
                        <h3 className="text-sm font-bold text-slate-300 font-display">Faithfulness & Hallucinations</h3>
                        <p className="text-[10px] text-slate-500">Daily average score vs hallucination percentage</p>
                      </div>

                      <div className="h-44 w-full flex items-center justify-center bg-slate-950/60 border border-slate-900/60 rounded-xl relative overflow-hidden">
                        {analyticsData.daily_stats && analyticsData.daily_stats.length >= 2 ? (
                          (() => {
                            const faithChart = drawSparkline(analyticsData.daily_stats, 'avg_faithfulness', 400, 160);
                            const halChart = drawSparkline(analyticsData.daily_stats, 'hallucination_rate', 400, 160);
                            if (!faithChart || !halChart) return null;
                            return (
                              <svg className="w-full h-full" viewBox="0 0 400 160">
                                <line x1="15" y1="80" x2="385" y2="80" stroke="rgba(255,255,255,0.03)" strokeDasharray="3,3" />
                                
                                {/* Faithfulness Line (Green) */}
                                <path d={faithChart.pathData} fill="none" stroke="#10b981" strokeWidth="2.5" />
                                {faithChart.points.map((p, i) => (
                                  <circle key={`f-${i}`} cx={p.x} cy={p.y} r="2.5" fill="#10b981" />
                                ))}

                                {/* Hallucination Line (Red) */}
                                <path d={halChart.pathData} fill="none" stroke="#ef4444" strokeWidth="2" strokeDasharray="4,2" />
                                {halChart.points.map((p, i) => (
                                  <circle key={`h-${i}`} cx={p.x} cy={p.y} r="2.5" fill="#ef4444" />
                                ))}

                                {/* Dates labels */}
                                {faithChart.points.map((p, i) => (
                                  (i === 0 || i === faithChart.points.length - 1) && (
                                    <text key={`d-${i}`} x={p.x} y={150} fill="#6b7280" fontSize="7" textAnchor={i === 0 ? 'start' : 'end'}>
                                      {p.date.slice(5)}
                                    </text>
                                  )
                                ))}

                                {/* Legend overlay */}
                                <g transform="translate(20, 20)">
                                  <circle cx="0" cy="0" r="3" fill="#10b981" />
                                  <text x="8" y="3" fill="#9ca3af" fontSize="7">Faithfulness</text>
                                  <circle cx="70" cy="0" r="3" fill="#ef4444" />
                                  <text x="78" y="3" fill="#9ca3af" fontSize="7">Hallucinations</text>
                                </g>
                              </svg>
                            );
                          })()
                        ) : (
                          <span className="text-xs text-slate-600 italic">Not enough historical daily records to graph.</span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Recent Logs Table */}
                  <div className="bg-slate-950/40 border border-slate-900 rounded-2xl overflow-hidden p-6 space-y-4">
                    <div>
                      <h3 className="text-sm font-bold text-slate-300 font-display">Recent Pipeline Evaluations</h3>
                      <p className="text-[10px] text-slate-500">Live records from the active chat evaluations log</p>
                    </div>

                    <div className="overflow-x-auto border border-slate-900 rounded-xl">
                      <table className="w-full text-left text-xs border-collapse">
                        <thead>
                          <tr className="bg-slate-950 text-slate-500 border-b border-slate-900">
                            <th className="p-3 font-semibold">User Query</th>
                            <th className="p-3 font-semibold text-center">Faithful</th>
                            <th className="p-3 font-semibold text-center">Relevance</th>
                            <th className="p-3 font-semibold text-center">Precision</th>
                            <th className="p-3 font-semibold text-center">Recall</th>
                            <th className="p-3 font-semibold text-center">Latency</th>
                            <th className="p-3 font-semibold text-right">Timestamp</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-900/60">
                          {analyticsData.recent_evaluations.map((ev) => (
                            <tr key={ev.id} className="hover:bg-slate-900/20 text-slate-300">
                              <td className="p-3 font-medium truncate max-w-xs" title={ev.user_query}>
                                {ev.user_query}
                              </td>
                              <td className="p-3 text-center font-bold">
                                <span className={ev.faithfulness_score >= 0.8 ? 'text-emerald-400' : 'text-rose-400'}>
                                  {(ev.faithfulness_score * 100).toFixed(0)}%
                                </span>
                              </td>
                              <td className="p-3 text-center">
                                {(ev.answer_relevance_score * 100).toFixed(0)}%
                              </td>
                              <td className="p-3 text-center">
                                {(ev.context_precision_score * 100).toFixed(0)}%
                              </td>
                              <td className="p-3 text-center">
                                {(ev.context_recall_score * 100).toFixed(0)}%
                              </td>
                              <td className="p-3 text-center text-cyan-400">
                                {ev.latency_ms ? ev.latency_ms.toFixed(0) : '0'} ms
                              </td>
                              <td className="p-3 text-right text-slate-500">
                                {new Date(ev.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>

                </div>
              )}
            </div>
          </>
          } />
        </Routes>

      </div>
    </div>
  );
}
