import { formatNumber, breakoutColor, vphDisplay, formatEngagement } from '../utils/helpers';

export default function CompareView({ videos, onClose }) {
  if (!videos || videos.length === 0) return null;

  return (
    <>
      <div className="fixed inset-0 bg-black/70 z-50 animate-fade-in" onClick={onClose} />
      
      <div className="fixed inset-4 md:inset-10 bg-[var(--color-bg-primary)] border border-[var(--color-border)] rounded-2xl shadow-2xl z-50 flex flex-col animate-slide-in overflow-hidden">
        
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--color-border)] bg-[var(--color-bg-secondary)]">
          <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">Compare Videos</h2>
          <button onClick={onClose} className="text-2xl text-[var(--color-text-muted)] hover:text-white transition-colors">✕</button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6">
          <div className="grid gap-6" style={{ gridTemplateColumns: `repeat(${videos.length}, minmax(300px, 1fr))` }}>
            {videos.map(video => {
              const bc = breakoutColor(video.breakout_score);
              const vph = vphDisplay(video.vph);
              
              return (
                <div key={video.video_id} className="bg-[var(--color-bg-card)] rounded-xl border border-[var(--color-border)] overflow-hidden">
                  <img src={video.thumbnail_url} alt="" className="w-full aspect-video object-cover" />
                  
                  <div className="p-4 space-y-4">
                    <div>
                      <h3 className="font-semibold text-[var(--color-text-primary)] line-clamp-2" title={video.title}>{video.title}</h3>
                      <p className="text-sm text-[var(--color-text-secondary)] mt-1">{video.channel_title} • {formatNumber(video.subscriber_count)} subs</p>
                    </div>

                    <div className="space-y-3 pt-3 border-t border-[var(--color-border)]">
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-[var(--color-text-muted)]">Breakout Score</span>
                        <span className={`px-2 py-0.5 rounded-full text-xs font-bold border ${bc.bg} ${bc.text} ${bc.border} ${bc.glow ? 'animate-pulse-glow' : ''}`}>
                          {video.breakout_score.toFixed(1)}x
                        </span>
                      </div>
                      
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-[var(--color-text-muted)]">Velocity (VPH)</span>
                        <span className={`font-mono text-sm ${vph.fire ? 'text-[var(--color-fire)]' : 'text-white'}`}>
                          {vph.text}/h
                        </span>
                      </div>

                      <div className="flex justify-between items-center">
                        <span className="text-sm text-[var(--color-text-muted)]">Total Views</span>
                        <span className="font-mono text-sm text-white">{formatNumber(video.view_count)}</span>
                      </div>

                      <div className="flex justify-between items-center">
                        <span className="text-sm text-[var(--color-text-muted)]">Engagement</span>
                        <span className={`text-sm ${video.engagement_rate < 0.02 ? 'text-[var(--color-danger)]' : 'text-white'}`}>
                          {formatEngagement(video.engagement_rate)}
                        </span>
                      </div>
                      
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-[var(--color-text-muted)]">Format</span>
                        <span className="text-sm text-white">{video.is_short ? 'Short' : 'Long-form'}</span>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </>
  );
}
