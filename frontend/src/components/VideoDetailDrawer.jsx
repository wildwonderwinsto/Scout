import { useEffect, useState } from 'react';
import { formatNumber, breakoutColor, vphDisplay, formatEngagement, formatTimeAgo } from '../utils/helpers';
import { fetchChannelAnalysis } from '../services/api';

export default function VideoDetailDrawer({ video, onClose }) {
  const [channelHealth, setChannelHealth] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('performance');

  useEffect(() => {
    if (video?.channel_id) {
      setLoading(true);
      fetchChannelAnalysis(video.channel_id)
        .then(data => setChannelHealth(data))
        .catch(err => console.error('Channel analysis failed:', err))
        .finally(() => setLoading(false));
    }
  }, [video?.channel_id]);

  if (!video) return null;

  const bc = breakoutColor(video.breakout_score);
  const vph = vphDisplay(video.vph);

  return (
    <>
      {/* Overlay */}
      <div
        className="fixed inset-0 bg-black/50 z-40 animate-fade-in"
        onClick={onClose}
      />

      {/* Drawer */}
      <div className="fixed top-0 right-0 h-full w-full max-w-2xl z-50 bg-[var(--color-bg-secondary)] border-l border-[var(--color-border)] overflow-y-auto animate-slide-in shadow-2xl">

        {/* ── Header ──────────────────────────── */}
        <div className="sticky top-0 z-10 flex items-center justify-between px-6 py-4 border-b border-[var(--color-border)] bg-[var(--color-bg-secondary)]">
          <h2 className="text-lg font-semibold text-[var(--color-text-primary)] truncate pr-4">
            Video Details
          </h2>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-[var(--color-bg-hover)] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors text-xl"
          >
            ✕
          </button>
        </div>

        <div className="p-6 space-y-6">

          {/* ── Video Hero ────────────────────── */}
          <div>
            <a
              href={`https://www.youtube.com/watch?v=${video.video_id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="block relative group"
            >
              <img
                src={video.thumbnail_url}
                alt={video.title}
                className="w-full rounded-xl object-cover aspect-video bg-[var(--color-bg-hover)]"
              />
              <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-black/30 rounded-xl">
                <span className="text-4xl">▶</span>
              </div>
            </a>
            <h3 className="mt-3 text-base font-semibold text-[var(--color-text-primary)] leading-tight">
              {video.title}
            </h3>
            <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
              {video.channel_title} • {formatNumber(video.subscriber_count)} subscribers
            </p>
          </div>

          {/* ── Metrics Cards ─────────────────── */}
          <div className="grid grid-cols-4 gap-3">
            <MetricCard
              label="Breakout"
              value={`${video.breakout_score.toFixed(1)}x`}
              className={`${bc.bg} ${bc.text} border ${bc.border} ${bc.glow ? 'animate-pulse-glow' : ''}`}
            />
            <MetricCard
              label="Views/Hour"
              value={vph.text}
              className={vph.fire ? 'text-[var(--color-fire)]' : ''}
            />
            <MetricCard label="Views" value={formatNumber(video.view_count)} />
            <MetricCard label="Engagement" value={formatEngagement(video.engagement_rate)} />
          </div>

          {/* ── Detail Grid ───────────────────── */}
          <div className="grid grid-cols-2 gap-3 text-sm">
            <DetailRow label="Published" value={formatTimeAgo(video.published_days_ago)} />
            <DetailRow label="Format" value={video.is_short ? 'Short' : 'Long-form'} />
            <DetailRow label="Duration" value={video.duration_seconds ? `${Math.floor(video.duration_seconds / 60)}m ${video.duration_seconds % 60}s` : '—'} />
            <DetailRow label="Likes" value={formatNumber(video.like_count)} />
            <DetailRow label="Comments" value={formatNumber(video.comment_count)} />
            <DetailRow label="VPH Source" value={video.vph_source === 'snapshot' ? 'Real-time' : 'Lifetime avg'} />
            <DetailRow label="Channel Avg" value={formatNumber(video.channel_avg_views)} />
            <DetailRow label="Channel Subs" value={formatNumber(video.subscriber_count)} />
          </div>

          {/* ── Tabs ──────────────────────────── */}
          <div className="border-t border-[var(--color-border)] pt-4">
            <div className="flex gap-1 mb-4">
              {['performance', 'channel', 'seo'].map(tab => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`px-3 py-1.5 text-xs font-medium rounded-lg capitalize transition-all
                    ${activeTab === tab
                      ? 'bg-[var(--color-accent)] text-white'
                      : 'bg-[var(--color-bg-hover)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-active)]'
                    }`}
                >
                  {tab === 'seo' ? 'SEO' : tab.charAt(0).toUpperCase() + tab.slice(1)}
                </button>
              ))}
            </div>

            {/* Performance Tab */}
            {activeTab === 'performance' && (
              <div className="space-y-3 animate-fade-in">
                <div className="p-4 rounded-xl bg-[var(--color-bg-card)] border border-[var(--color-border)]">
                  <h4 className="text-xs font-semibold text-[var(--color-text-muted)] uppercase mb-3">Performance Summary</h4>
                  <div className="space-y-2 text-sm">
                    <p className="text-[var(--color-text-secondary)]">
                      This video has <span className="text-[var(--color-text-primary)] font-semibold">{video.breakout_score.toFixed(1)}x</span> more views than the channel's average ({formatNumber(video.channel_avg_views)} views).
                    </p>
                    <p className="text-[var(--color-text-secondary)]">
                      It's gaining <span className="text-[var(--color-text-primary)] font-semibold">{formatNumber(Math.round(video.vph))}</span> views per hour
                      {video.vph_source === 'snapshot' ? ' (measured from real-time snapshots)' : ' (estimated from lifetime average)'}.
                    </p>
                    {video.engagement_flag && (
                      <div className="flex gap-2 items-start text-xs text-[var(--color-danger)] mt-2 bg-[var(--color-danger)]/10 p-2 rounded">
                        <svg className="w-4 h-4 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
                        <span>Engagement is suspiciously low compared to channel average. This may indicate promoted or artificial views.</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Channel Tab */}
            {activeTab === 'channel' && (
              <div className="space-y-3 animate-fade-in">
                {loading ? (
                  <div className="space-y-3">
                    {[1,2,3].map(i => (
                      <div key={i} className="h-16 rounded-xl animate-shimmer" />
                    ))}
                  </div>
                ) : channelHealth?.health ? (
                  <div className="p-4 rounded-xl bg-[var(--color-bg-card)] border border-[var(--color-border)]">
                    <h4 className="text-xs font-semibold text-[var(--color-text-muted)] uppercase mb-3">Channel Health</h4>
                    <div className="grid grid-cols-2 gap-3 text-sm">
                      <DetailRow label="Videos (7d)" value={channelHealth.health.videos_last_7d} />
                      <DetailRow label="Videos (30d)" value={channelHealth.health.videos_last_30d} />
                      <DetailRow label="Shorts Ratio" value={`${(channelHealth.health.shorts_ratio * 100).toFixed(0)}%`} />
                      <DetailRow label="Upload Frequency" value={channelHealth.health.avg_days_between_uploads ? `Every ${channelHealth.health.avg_days_between_uploads}d` : '—'} />
                      <DetailRow label="Last Upload" value={channelHealth.health.last_upload_days_ago != null ? `${channelHealth.health.last_upload_days_ago}d ago` : '—'} />
                      <DetailRow label="Consistency" value={
                        <span className={`px-2 py-0.5 rounded-full text-xs font-semibold
                          ${channelHealth.health.posting_consistency === 'high' ? 'bg-green-900/40 text-green-400' :
                            channelHealth.health.posting_consistency === 'medium' ? 'bg-yellow-900/40 text-yellow-400' :
                            channelHealth.health.posting_consistency === 'low' ? 'bg-orange-900/40 text-orange-400' :
                            'bg-red-900/40 text-red-400'
                          }`}
                        >
                          {channelHealth.health.posting_consistency}
                        </span>
                      } />
                    </div>
                    {channelHealth.outlier_count > 0 && (
                      <p className="mt-3 text-xs text-[var(--color-text-muted)]">
                        This channel has {channelHealth.outlier_count} outlier video{channelHealth.outlier_count > 1 ? 's' : ''} (breakout ≥ 2x).
                      </p>
                    )}
                  </div>
                ) : (
                  <div className="p-4 rounded-xl bg-[var(--color-bg-card)] border border-[var(--color-border)] text-sm text-[var(--color-text-muted)]">
                    Channel health data unavailable.
                  </div>
                )}
              </div>
            )}

            {/* SEO Tab */}
            {activeTab === 'seo' && (
              <div className="space-y-3 animate-fade-in">
                <div className="p-4 rounded-xl bg-[var(--color-bg-card)] border border-[var(--color-border)]">
                  <h4 className="text-xs font-semibold text-[var(--color-text-muted)] uppercase mb-3">SEO Signals</h4>
                  <div className="space-y-2 text-sm text-[var(--color-text-secondary)]">
                    <p><span className="text-[var(--color-text-muted)]">Title length:</span> {video.title.length} characters {video.title.length <= 60 ? '(Good)' : '(Over 60)'}</p>
                    <p><span className="text-[var(--color-text-muted)]">Has emoji:</span> {/[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1F1E0}-\u{1F1FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/u.test(video.title) ? 'Yes' : 'No'}</p>
                    <p><span className="text-[var(--color-text-muted)]">Has numbers:</span> {/\d/.test(video.title) ? 'Yes' : 'No'}</p>
                  </div>
                </div>
                <div className="p-4 rounded-xl bg-[var(--color-bg-card)] border border-[var(--color-border)]">
                  <div className="p-4 rounded-xl border border-dashed border-[var(--color-border)] bg-blue-900/10 flex items-center justify-center">
                    <p className="text-xs text-blue-400 text-center max-w-[200px]">
                      Connect vidIQ or TubeBuddy API to enable keyword volume, competition scores, and related keyword suggestions.
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* ── YouTube link ──────────────────── */}
          <a
            href={`https://www.youtube.com/watch?v=${video.video_id}`}
            target="_blank"
            rel="noopener noreferrer"
            className="block w-full text-center py-2.5 rounded-lg bg-red-600 hover:bg-red-500 text-white text-sm font-semibold transition-colors"
          >
            Watch on YouTube →
          </a>
        </div>
      </div>
    </>
  );
}

function MetricCard({ label, value, className = '' }) {
  return (
    <div className={`p-3 rounded-xl bg-[var(--color-bg-card)] border border-[var(--color-border)] text-center ${className}`}>
      <p className="text-xs text-[var(--color-text-muted)] mb-1">{label}</p>
      <p className="text-lg font-bold">{value}</p>
    </div>
  );
}

function DetailRow({ label, value }) {
  return (
    <div className="flex justify-between items-center py-1.5 px-3 rounded-lg bg-[var(--color-bg-card)]/50">
      <span className="text-xs text-[var(--color-text-muted)]">{label}</span>
      <span className="text-sm text-[var(--color-text-primary)]">{value}</span>
    </div>
  );
}
