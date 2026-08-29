import { useState, useEffect } from 'react';
import FilterBar from './components/FilterBar';
import ResultsTable from './components/ResultsTable';
import VideoDetailDrawer from './components/VideoDetailDrawer';
import SavedList from './components/SavedList';
import CompareView from './components/CompareView';
import { fetchGeneralScan, fetchKeywordScan, fetchChannelScan } from './services/api';
import { getSavedVideos, saveVideo, unsaveVideo } from './utils/helpers';

export default function App() {
  const [scanMode, setScanMode] = useState('keyword'); // 'general', 'keyword', 'channel'
  const [results, setResults] = useState([]);
  const [scanMeta, setScanMeta] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const [selectedVideo, setSelectedVideo] = useState(null);
  
  const [savedVideos, setSavedVideos] = useState([]);
  const [showSaved, setShowSaved] = useState(false);
  
  const [compareMode, setCompareMode] = useState(false);
  const [compareSelection, setCompareSelection] = useState([]);
  const [showCompareView, setShowCompareView] = useState(false);

  // Load saved videos on mount
  useEffect(() => {
    setSavedVideos(getSavedVideos());
  }, []);

  const handleApplyFilters = async (filters, channelIdOrUrl) => {
    setLoading(true);
    setError(null);
    setResults([]);
    setShowSaved(false);
    
    try {
      let data;
      if (scanMode === 'keyword') {
        data = await fetchKeywordScan(filters);
      } else if (scanMode === 'general') {
        data = await fetchGeneralScan(filters);
      } else if (scanMode === 'channel') {
        if (!channelIdOrUrl) throw new Error("Please enter a channel ID or URL");
        data = await fetchChannelScan(encodeURIComponent(channelIdOrUrl), filters);
      }
      
      setResults(data.results || []);
      setScanMeta({
        scan_type: data.scan_type,
        query: data.query,
        total_channels_scanned: data.total_channels_scanned,
        total_videos_evaluated: data.total_videos_evaluated,
      });
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || err.message || 'An error occurred during scan.');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveToggle = (video) => {
    const isSaved = savedVideos.some(v => v.video_id === video.video_id);
    if (isSaved) {
      setSavedVideos(unsaveVideo(video.video_id));
      setCompareSelection(prev => prev.filter(id => id !== video.video_id));
    } else {
      setSavedVideos(saveVideo(video));
    }
  };

  const handleToggleCompare = (videoId) => {
    setCompareSelection(prev => 
      prev.includes(videoId) ? prev.filter(id => id !== videoId) : [...prev, videoId].slice(-3) // Max 3
    );
  };

  const videosToCompare = savedVideos.filter(v => compareSelection.includes(v.video_id));

  return (
    <div className="flex h-screen bg-[var(--color-bg-primary)] overflow-hidden text-[var(--color-text-primary)]">
      
      {/* ── Sidebar (FilterBar) ────────────────────────────────── */}
      <aside className="w-80 border-r border-[var(--color-border)] bg-[var(--color-bg-secondary)] flex flex-col flex-shrink-0 z-20 hidden md:flex">
        <div className="p-5 border-b border-[var(--color-border)] bg-[var(--color-bg-card)]">
          <div className="flex items-center gap-3 text-[var(--color-accent)]">
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            <h1 className="text-lg font-bold tracking-tight text-white">YouTube Trend Scout</h1>
          </div>
        </div>
        <div className="flex-1 overflow-hidden">
          <FilterBar 
            onApplyFilters={handleApplyFilters} 
            loading={loading}
            scanMode={scanMode}
            onScanModeChange={setScanMode}
          />
        </div>
      </aside>

      {/* ── Main Content Area ──────────────────────────────────── */}
      <main className="flex-1 flex flex-col min-w-0 relative">
        
        {/* Top Navbar */}
        <header className="h-16 border-b border-[var(--color-border)] bg-[var(--color-bg-primary)] flex items-center justify-between px-6 flex-shrink-0">
          <div className="flex items-center gap-4">
            <h2 className="text-lg font-semibold hidden md:block">
              {showSaved ? 'Saved Videos' : 'Scan Results'}
            </h2>
          </div>
          
          <div className="flex items-center gap-3">
            <button
              onClick={() => { setShowSaved(false); setCompareMode(false); }}
              className={`px-4 py-1.5 text-sm font-medium rounded-lg transition-colors ${!showSaved ? 'bg-[var(--color-bg-active)] text-white' : 'text-[var(--color-text-secondary)] hover:text-white'}`}
            >
              Results
            </button>
            <button
              onClick={() => setShowSaved(true)}
              className={`flex items-center gap-2 px-4 py-1.5 text-sm font-medium rounded-lg transition-colors ${showSaved ? 'bg-[var(--color-bg-active)] text-white' : 'text-[var(--color-text-secondary)] hover:text-white'}`}
            >
              <svg className="w-4 h-4 text-[var(--color-accent)]" fill="currentColor" viewBox="0 0 20 20"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" /></svg>
              <span>Saved</span>
              <span className={`bg-[var(--color-accent)] text-white text-[10px] px-1.5 py-0.5 rounded-full min-w-[20px] text-center transition-opacity ${savedVideos.length > 0 ? 'opacity-100' : 'opacity-0'}`}>
                {savedVideos.length}
              </span>
            </button>
          </div>
        </header>

        {/* Error Banner */}
        {error && (
          <div className="bg-red-900/30 border-b border-red-500/30 px-6 py-3 flex items-center gap-2">
            <svg className="w-5 h-5 text-red-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
            <p className="text-sm text-red-400">{error}</p>
          </div>
        )}

        {/* Saved List Toolbar */}
        {showSaved && savedVideos.length > 0 && (
          <div className="bg-[var(--color-bg-secondary)] border-b border-[var(--color-border)] px-6 py-3 flex items-center justify-between">
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" checked={compareMode} onChange={e => setCompareMode(e.target.checked)} className="accent-[var(--color-accent)] w-4 h-4" />
              <span className="text-sm text-[var(--color-text-primary)] font-medium">Compare Mode</span>
            </label>
            
            {compareMode && (
              <button
                onClick={() => setShowCompareView(true)}
                disabled={compareSelection.length < 2}
                className="px-4 py-1.5 bg-[var(--color-accent)] text-white text-sm font-medium rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                Compare {compareSelection.length} {compareSelection.length === 3 ? '(Max)' : ''}
              </button>
            )}
          </div>
        )}

        {/* Content Body */}
        {showSaved ? (
          <SavedList 
            savedVideos={savedVideos} 
            onRemove={handleSaveToggle}
            onSelectVideo={setSelectedVideo}
            compareMode={compareMode}
            compareSelection={compareSelection}
            onToggleCompare={handleToggleCompare}
          />
        ) : (
          <ResultsTable 
            results={results} 
            scanMeta={scanMeta}
            loading={loading}
            onSelectVideo={setSelectedVideo}
            onSaveVideo={handleSaveToggle}
          />
        )}
        
      </main>

      {/* ── Modals & Drawers ───────────────────────────────────── */}
      {selectedVideo && (
        <VideoDetailDrawer 
          video={selectedVideo} 
          onClose={() => setSelectedVideo(null)} 
        />
      )}

      {showCompareView && (
        <CompareView 
          videos={videosToCompare} 
          onClose={() => setShowCompareView(false)} 
        />
      )}

    </div>
  );
}
