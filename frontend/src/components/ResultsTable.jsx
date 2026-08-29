import { formatNumber, breakoutColor, vphDisplay, formatEngagement, formatTimeAgo, isVideoSaved } from '../utils/helpers';

export default function ResultsTable({ results, onSelectVideo, onSaveVideo, scanMeta, loading }) {
  if (!results || results.length === 0) {
    let title = "Ready to search";
    let desc = "Configure your filters and click search to discover trending videos.";
    let icon = (
      <svg className="w-12 h-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
      </svg>
    );

    if (loading) {
      title = "Scanning YouTube...";
      desc = "Searching for outliers. This might take a few seconds.";
      icon = (
        <svg className="w-12 h-12 animate-spin text-[var(--color-accent)]" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
      );
    } else if (scanMeta) {
      title = "No results found";
      desc = "Try broadening your filters or searching a different keyword/channel.";
      icon = (
        <svg className="w-12 h-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      );
    }

    return (
      <div className="flex-1 flex items-center justify-center text-[var(--color-text-muted)]">
        <div className="text-center">
          <div className="flex justify-center mb-4 text-[var(--color-text-secondary)]">
            {icon}
          </div>
          <p className="text-lg font-medium text-[var(--color-text-primary)] mb-1">{title}</p>
          <p className="text-sm max-w-sm mx-auto">{desc}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* ── Scan meta bar ────────────────────────── */}
      {scanMeta && (
        <div className="flex items-center gap-4 px-4 py-2.5 border-b border-[var(--color-border)] bg-[var(--color-bg-secondary)]">
          <span className="text-xs text-[var(--color-text-muted)] font-medium">
            {scanMeta.scan_type === 'keyword' ? `Keyword Scan: "${scanMeta.query}"` : scanMeta.scan_type === 'channel' ? 'Channel Scan' : 'General Scan'}
          </span>
          <span className="text-xs text-[var(--color-text-muted)]">
            {scanMeta.total_channels_scanned} channels • {scanMeta.total_videos_evaluated} videos evaluated
          </span>
          <span className="text-xs text-[var(--color-text-muted)]">
            {results.length} results
          </span>
        </div>
      )}

      {/* ── Table ────────────────────────────────── */}
      <div className="flex-1 overflow-auto">
        <table className="w-full text-sm">
          <thead className="sticky top-0 z-10">
            <tr className="bg-[var(--color-bg-secondary)] border-b border-[var(--color-border)]">
              <th className="text-left px-3 py-2.5 text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider w-8">#</th>
              <th className="text-left px-3 py-2.5 text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider min-w-[300px]">Video</th>
              <th className="text-left px-3 py-2.5 text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">Channel</th>
              <th className="text-right px-3 py-2.5 text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">Views</th>
              <th className="text-right px-3 py-2.5 text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">Breakout</th>
              <th className="text-right px-3 py-2.5 text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">VPH</th>
              <th className="text-right px-3 py-2.5 text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">Engagement</th>
              <th className="text-right px-3 py-2.5 text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">Age</th>
              <th className="text-center px-3 py-2.5 text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider w-10"></th>
            </tr>
          </thead>
          <tbody>
            {results.map((video, idx) => {
              const bc = breakoutColor(video.breakout_score);
              const vph = vphDisplay(video.vph);
              const saved = isVideoSaved(video.video_id);
              const suspicious = video.engagement_flag || video.engagement_rate < 0.02;

              return (
                <tr
                  key={video.video_id}
                  onClick={() => onSelectVideo(video)}
                  className={`border-b border-[var(--color-border)]/50 cursor-pointer transition-all duration-150
                    hover:bg-[var(--color-bg-hover)] group
                    ${suspicious ? 'opacity-60' : ''}`}
                >
                  {/* Rank */}
                  <td className="px-3 py-3 text-xs text-[var(--color-text-muted)] font-mono">
                    {idx + 1}
                  </td>

                  {/* Video (thumbnail + title) */}
                  <td className="px-3 py-3">
                    <div className="flex items-center gap-3">
                      <img
                        src={video.thumbnail_url}
                        alt=""
                        className="w-24 h-14 rounded-md object-cover flex-shrink-0 bg-[var(--color-bg-hover)]"
                        loading="lazy"
                      />
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-[var(--color-text-primary)] truncate max-w-[280px] group-hover:text-[var(--color-accent-bright)] transition-colors">
                          {video.title}
                        </p>
                        <div className="flex items-center gap-2 mt-0.5">
                          {video.is_short && (
                            <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-red-900/40 text-red-400">
                              SHORT
                            </span>
                          )}
                          {suspicious && (
                            <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-[var(--color-danger)]/10 border border-[var(--color-danger)]/20 text-[var(--color-danger)]">
                              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
                              <span className="text-[10px] font-bold tracking-wider">LOW ENG</span>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </td>

                  {/* Channel */}
                  <td className="px-3 py-3">
                    <div>
                      <p className="text-sm text-[var(--color-text-secondary)] truncate max-w-[160px]">{video.channel_title}</p>
                      <p className="text-xs text-[var(--color-text-muted)]">
                        {formatNumber(video.subscriber_count)} subs • avg {formatNumber(video.channel_avg_views)}
                      </p>
                    </div>
                  </td>

                  {/* Views */}
                  <td className="px-3 py-3 text-right font-mono text-sm text-[var(--color-text-primary)]">
                    {formatNumber(video.view_count)}
                  </td>

                  {/* Breakout Score */}
                  <td className="px-3 py-3 text-right">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold border
                      ${bc.bg} ${bc.text} ${bc.border}
                      ${bc.glow ? 'animate-pulse-glow' : ''}`}
                    >
                      {video.breakout_score.toFixed(1)}x
                    </span>
                  </td>

                  {/* VPH */}
                  <td className="px-3 py-3 text-right font-mono text-sm">
                    <span className={`text-sm font-mono ${vph.fire ? 'text-[var(--color-fire)]' : 'text-[var(--color-text-secondary)]'}`}>
                      {vph.text}/h
                    </span>
                  </td>

                  {/* Engagement */}
                  <td className={`px-3 py-3 text-right text-sm
                    ${video.engagement_rate < 0.02 ? 'text-[var(--color-danger)]' : 'text-[var(--color-text-secondary)]'}`}>
                    {formatEngagement(video.engagement_rate)}
                  </td>

                  {/* Age */}
                  <td className="px-3 py-3 text-right text-xs text-[var(--color-text-muted)]">
                    {formatTimeAgo(video.published_days_ago)}
                  </td>

                  {/* Save */}
                  <td className="px-3 py-3 text-center">
                    <button
                      onClick={(e) => { e.stopPropagation(); onSaveVideo(video); }}
                      className="p-2 rounded-lg hover:bg-[var(--color-bg-active)] transition-colors"
                    >
                      {saved ? (
                        <svg className="w-5 h-5 text-[var(--color-accent)]" fill="currentColor" viewBox="0 0 20 20"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" /></svg>
                      ) : (
                        <svg className="w-5 h-5 text-[var(--color-text-muted)] hover:text-white transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" /></svg>
                      )}
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
