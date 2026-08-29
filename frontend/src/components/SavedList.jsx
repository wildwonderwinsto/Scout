import { formatNumber, breakoutColor, vphDisplay, formatEngagement, formatTimeAgo } from '../utils/helpers';

export default function SavedList({ savedVideos, onRemove, onSelectVideo, compareMode, compareSelection, onToggleCompare }) {
  if (!savedVideos || savedVideos.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-[var(--color-text-muted)]">
        <div className="text-center">
          <div className="flex justify-center mb-4 text-[var(--color-accent)]">
            <svg className="w-12 h-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
            </svg>
          </div>
          <p className="text-lg font-medium mb-1">No saved videos yet</p>
          <p className="text-sm">Click the star icon on any result to save it here.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-auto">
      <div className="p-4 space-y-2">
        {savedVideos.map((video) => {
          const bc = breakoutColor(video.breakout_score);
          const vph = vphDisplay(video.vph);
          const isSelected = compareSelection?.includes(video.video_id);

          return (
            <div
              key={video.video_id}
              onClick={() => onSelectVideo(video)}
              className={`flex items-center gap-3 p-3 rounded-xl border cursor-pointer transition-all
                ${isSelected
                  ? 'border-[var(--color-accent)] bg-[var(--color-accent-glow)]'
                  : 'border-[var(--color-border)] bg-[var(--color-bg-card)] hover:bg-[var(--color-bg-hover)]'
                }`}
            >
              {/* Compare checkbox */}
              {compareMode && (
                <input
                  type="checkbox"
                  checked={isSelected}
                  onChange={(e) => { e.stopPropagation(); onToggleCompare(video.video_id); }}
                  className="w-4 h-4 accent-[var(--color-accent)] flex-shrink-0"
                />
              )}

              {/* Thumbnail */}
              <img
                src={video.thumbnail_url}
                alt=""
                className="w-20 h-12 rounded-md object-cover flex-shrink-0 bg-[var(--color-bg-hover)]"
              />

              {/* Info */}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-[var(--color-text-primary)] truncate">{video.title}</p>
                <p className="text-xs text-[var(--color-text-muted)]">{video.channel_title}</p>
              </div>

              {/* Metrics */}
              <div className="flex items-center gap-3 flex-shrink-0">
                <span className={`text-xs font-bold px-2 py-0.5 rounded-full border ${bc.bg} ${bc.text} ${bc.border}`}>
                  {video.breakout_score.toFixed(1)}x
                </span>
                <span className={`text-xs font-mono w-16 text-right ${vph.fire ? 'text-[var(--color-fire)]' : 'text-[var(--color-text-muted)]'}`}>
                  {vph.text}/h
                </span>
              </div>

              {/* Remove */}
              <button
                onClick={(e) => { e.stopPropagation(); onRemove(video); }}
                className="p-1 rounded hover:bg-[var(--color-bg-active)] text-[var(--color-text-muted)] hover:text-[var(--color-danger)] transition-colors text-sm flex-shrink-0"
                title="Remove from saved"
              >
                ✕
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
