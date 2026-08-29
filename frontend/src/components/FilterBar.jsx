import { useState } from 'react';

const RECENCY_OPTIONS = [
  { label: '3 days', value: 3 },
  { label: '7 days', value: 7 },
  { label: '14 days', value: 14 },
  { label: '30 days', value: 30 },
  { label: '90 days', value: 90 },
];

const FORMAT_OPTIONS = [
  { label: 'All', value: 'all' },
  { label: 'Shorts', value: 'short' },
  { label: 'Long-form', value: 'long' },
];

const SORT_OPTIONS = [
  { label: 'Breakout Score', value: 'breakout' },
  { label: 'Views/Hour', value: 'vph' },
  { label: 'Total Views', value: 'views' },
  { label: 'Newest', value: 'date' },
];

const BREAKOUT_OPTIONS = [
  { label: '1x+', value: 1 },
  { label: '2x+', value: 2 },
  { label: '3x+', value: 3 },
  { label: '5x+', value: 5 },
  { label: '10x+', value: 10 },
];

export default function FilterBar({ onApplyFilters, loading, scanMode, onScanModeChange }) {
  const [subscriberMin, setSubscriberMin] = useState(1000);
  const [subscriberMax, setSubscriberMax] = useState(200000);
  const [publishedDaysAgo, setPublishedDaysAgo] = useState(7);
  const [videoFormat, setVideoFormat] = useState('all');
  const [sortBy, setSortBy] = useState('breakout');
  const [minBreakout, setMinBreakout] = useState(2);
  const [minVph, setMinVph] = useState(0);
  const [minEngagement, setMinEngagement] = useState(0);
  const [query, setQuery] = useState('');
  const [channelInput, setChannelInput] = useState('');
  const [maxResults, setMaxResults] = useState(50);
  const [onlyActive, setOnlyActive] = useState(false);
  const [channelVideoMax, setChannelVideoMax] = useState('');
  const [minViews, setMinViews] = useState('');
  const [maxViews, setMaxViews] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();

    const filters = {
      subscriber_min: subscriberMin,
      subscriber_max: subscriberMax,
      languages: ['en'],
      countries: ['US', 'GB', 'CA', 'AU', 'NZ', 'IE'],
      published_days_ago: publishedDaysAgo,
      video_format: videoFormat,
      sort_by: sortBy,
      min_breakout: minBreakout,
      min_vph: minVph,
      min_engagement_rate: minEngagement,
      max_results: maxResults,
      min_recent_videos: onlyActive ? 3 : 0,
    };

    if (channelVideoMax !== '' && Number(channelVideoMax) > 0) {
      filters.channel_video_max = Number(channelVideoMax);
    }
    
    if (minViews !== '' && Number(minViews) >= 0) {
      filters.min_views = Number(minViews);
    }
    
    if (maxViews !== '' && Number(maxViews) > 0) {
      filters.max_views = Number(maxViews);
    }

    if (scanMode === 'keyword' && query.trim()) {
      filters.query = query.trim();
    }

    onApplyFilters(filters, scanMode === 'channel' ? channelInput.trim() : null);
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col h-full">
      {/* ── Header ───────────────────────────────── */}
      <div className="h-16 px-5 border-b border-[var(--color-border)] flex items-center">
        <h2 className="text-sm font-semibold tracking-wider uppercase text-[var(--color-text-muted)]">
          Search Filters
        </h2>
      </div>

      {/* ── Scrollable filters ───────────────────── */}
      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5">
        
        {/* Scan Mode Tabs */}
        <div>
          <label className="block text-xs font-medium text-[var(--color-text-muted)] mb-1.5">
            Scan Mode
          </label>
          <div className="flex gap-1">
            {['general', 'keyword', 'channel'].map(mode => (
              <button
                key={mode}
                type="button"
                onClick={() => onScanModeChange(mode)}
                className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-all duration-200 capitalize flex-1
                  ${scanMode === mode
                    ? 'bg-[var(--color-accent)] text-white shadow-lg shadow-indigo-500/20'
                    : 'bg-[var(--color-bg-hover)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-active)]'
                  }`}
              >
                {mode}
              </button>
            ))}
          </div>
        </div>

        {/* Query input (keyword mode) */}
        {scanMode === 'keyword' && (
          <div>
            <label className="block text-xs font-medium text-[var(--color-text-muted)] mb-1.5">
              Search Keywords
            </label>
            <input
              type="text"
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="e.g. faceless channel ideas"
              className="w-full px-3 py-2 rounded-lg bg-[var(--color-bg-hover)] border border-[var(--color-border)]
                text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)]
                focus:outline-none focus:border-[var(--color-accent)] transition-colors"
            />
          </div>
        )}

        {/* Channel input (channel mode) */}
        {scanMode === 'channel' && (
          <div>
            <label className="block text-xs font-medium text-[var(--color-text-muted)] mb-1.5">
              Channel ID, Handle, or URL
            </label>
            <input
              type="text"
              value={channelInput}
              onChange={e => setChannelInput(e.target.value)}
              placeholder="@MrBeast or UC..."
              className="w-full px-3 py-2 rounded-lg bg-[var(--color-bg-hover)] border border-[var(--color-border)]
                text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)]
                focus:outline-none focus:border-[var(--color-accent)] transition-colors"
            />
          </div>
        )}

        {/* Subscriber Band (Hidden in Channel Mode) */}
        {scanMode !== 'channel' && (
          <div>
            <label className="block text-xs font-medium text-[var(--color-text-muted)] mb-1.5">
              Subscriber Range
            </label>
            <div className="flex gap-2 items-center">
              <input
                type="number"
                value={subscriberMin}
                onChange={e => setSubscriberMin(Number(e.target.value))}
                className="w-full px-2 py-1.5 rounded-lg bg-[var(--color-bg-hover)] border border-[var(--color-border)]
                  text-sm text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)]"
                min={0}
              />
              <span className="text-[var(--color-text-muted)] text-xs">to</span>
              <input
                type="number"
                value={subscriberMax}
                onChange={e => setSubscriberMax(Number(e.target.value))}
                className="w-full px-2 py-1.5 rounded-lg bg-[var(--color-bg-hover)] border border-[var(--color-border)]
                  text-sm text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)]"
                min={0}
              />
            </div>
          </div>
        )}

        {/* View Count Range */}
        <div>
          <label className="block text-xs font-medium text-[var(--color-text-muted)] mb-1.5">
            View Count Range
          </label>
          <div className="flex gap-2 items-center">
            <input
              type="number"
              value={minViews}
              onChange={e => setMinViews(e.target.value)}
              placeholder="Min"
              className="w-full px-2 py-1.5 rounded-lg bg-[var(--color-bg-hover)] border border-[var(--color-border)]
                text-sm text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)]"
              min={0}
            />
            <span className="text-[var(--color-text-muted)] text-xs">to</span>
            <input
              type="number"
              value={maxViews}
              onChange={e => setMaxViews(e.target.value)}
              placeholder="Max"
              className="w-full px-2 py-1.5 rounded-lg bg-[var(--color-bg-hover)] border border-[var(--color-border)]
                text-sm text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)]"
              min={0}
            />
          </div>
        </div>

        {/* Max Channel Videos (Hidden in Channel Mode) */}
        {scanMode !== 'channel' && (
          <div>
            <label className="block text-xs font-medium text-[var(--color-text-muted)] mb-1.5">
              Max Channel Videos
            </label>
            <input
              type="number"
              value={channelVideoMax}
              onChange={e => setChannelVideoMax(e.target.value)}
              placeholder="No limit"
              className="w-full px-3 py-2 rounded-lg bg-[var(--color-bg-hover)] border border-[var(--color-border)]
                text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)]
                focus:outline-none focus:border-[var(--color-accent)] transition-colors"
              min={1}
            />
            <p className="mt-1 text-[10px] text-[var(--color-text-muted)]">
              Find early channels with fewer total uploads
            </p>
          </div>
        )}

        {/* Recency */}
        <div>
          <label className="block text-xs font-medium text-[var(--color-text-muted)] mb-1.5">
            Published Within
          </label>
          <div className="flex flex-wrap gap-1.5">
            {RECENCY_OPTIONS.map(opt => (
              <button
                key={opt.value}
                type="button"
                onClick={() => setPublishedDaysAgo(opt.value)}
                className={`px-3 py-1 text-xs rounded-full transition-all
                  ${publishedDaysAgo === opt.value
                    ? 'bg-[var(--color-accent)] text-white'
                    : 'bg-[var(--color-bg-hover)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-active)]'
                  }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* Format */}
        <div>
          <label className="block text-xs font-medium text-[var(--color-text-muted)] mb-1.5">
            Video Format
          </label>
          <div className="flex gap-1.5">
            {FORMAT_OPTIONS.map(opt => (
              <button
                key={opt.value}
                type="button"
                onClick={() => setVideoFormat(opt.value)}
                className={`px-3 py-1 text-xs rounded-full transition-all flex-1
                  ${videoFormat === opt.value
                    ? 'bg-[var(--color-accent)] text-white'
                    : 'bg-[var(--color-bg-hover)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-active)]'
                  }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* Min Breakout */}
        <div>
          <label className="block text-xs font-medium text-[var(--color-text-muted)] mb-1.5">
            Min Breakout Score
          </label>
          <div className="flex flex-wrap gap-1.5">
            {BREAKOUT_OPTIONS.map(opt => (
              <button
                key={opt.value}
                type="button"
                onClick={() => setMinBreakout(opt.value)}
                className={`px-3 py-1 text-xs rounded-full transition-all
                  ${minBreakout === opt.value
                    ? 'bg-[var(--color-accent)] text-white'
                    : 'bg-[var(--color-bg-hover)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-active)]'
                  }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* Sort */}
        <div>
          <label className="block text-xs font-medium text-[var(--color-text-muted)] mb-1.5">
            Sort By
          </label>
          <select
            value={sortBy}
            onChange={e => setSortBy(e.target.value)}
            className="w-full px-3 py-2 rounded-lg bg-[var(--color-bg-hover)] border border-[var(--color-border)]
              text-sm text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)]"
          >
            {SORT_OPTIONS.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>

        {/* Min VPH */}
        <div>
          <label className="block text-xs font-medium text-[var(--color-text-muted)] mb-1.5">
            Min VPH (Views/Hour)
          </label>
          <input
            type="number"
            value={minVph}
            onChange={e => setMinVph(Number(e.target.value))}
            className="w-full px-3 py-2 rounded-lg bg-[var(--color-bg-hover)] border border-[var(--color-border)]
              text-sm text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)]"
            min={0}
          />
        </div>

        {/* Max Results */}
        <div>
          <label className="block text-xs font-medium text-[var(--color-text-muted)] mb-1.5">
            Max Results
          </label>
          <input
            type="number"
            value={maxResults}
            onChange={e => setMaxResults(Number(e.target.value))}
            className="w-full px-3 py-2 rounded-lg bg-[var(--color-bg-hover)] border border-[var(--color-border)]
              text-sm text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)]"
            min={1}
            max={200}
          />
        </div>

        {/* Only Active Channels (Hidden in Channel Mode) */}
        {scanMode !== 'channel' && (
          <label className="flex items-center gap-2 cursor-pointer group">
            <input
              type="checkbox"
              checked={onlyActive}
              onChange={e => setOnlyActive(e.target.checked)}
              className="w-4 h-4 rounded border-[var(--color-border)] accent-[var(--color-accent)]"
            />
            <span className="text-xs text-[var(--color-text-secondary)] group-hover:text-[var(--color-text-primary)] transition-colors">
              Only active channels (3+ videos/week)
            </span>
          </label>
        )}
      </div>

      {/* ── Submit ────────────────────────────────── */}
      <div className="px-5 py-4 border-t border-[var(--color-border)]">
        <button
          type="submit"
          disabled={loading}
          className={`w-full py-2.5 rounded-lg text-sm font-semibold transition-all duration-200
            ${loading
              ? 'bg-[var(--color-bg-active)] text-[var(--color-text-muted)] cursor-wait'
              : 'bg-[var(--color-accent)] text-white hover:bg-[var(--color-accent-bright)] shadow-lg shadow-indigo-500/25 hover:shadow-indigo-500/40'
            }`}
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Scanning...
            </span>
          ) : (
            `Run ${scanMode.charAt(0).toUpperCase() + scanMode.slice(1)} Scan`
          )}
        </button>
      </div>
    </form>
  );
}
