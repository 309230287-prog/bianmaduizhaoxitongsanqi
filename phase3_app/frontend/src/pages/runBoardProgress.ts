export type RunMetricsLike = {
  total_count: number;
  auto_code_count: number;
  suggested_review_count: number;
  manual_review_count: number;
  no_reliable_match_count: number;
};

export function processedCount(metrics: RunMetricsLike | undefined): number {
  if (!metrics) return 0;
  return (
    metrics.auto_code_count
    + metrics.manual_review_count
    + metrics.no_reliable_match_count
    + metrics.suggested_review_count
  );
}

export function progressPercent(metrics: RunMetricsLike | undefined): number {
  if (!metrics || metrics.total_count <= 0) return 0;
  return Math.min(100, Math.round((processedCount(metrics) / metrics.total_count) * 100));
}
