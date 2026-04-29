import { progressPercent, processedCount } from "./runBoardProgress";

const sampleMetrics = {
  total_count: 10,
  auto_code_count: 2,
  auto_code_with_diff_count: 0,
  suggested_review_count: 1,
  manual_review_count: 3,
  no_reliable_match_count: 2,
  returned_to_nature_count: 0,
  hard_case_count: 0,
  total_rounds: 1,
};

if (processedCount(sampleMetrics) !== 8) {
  throw new Error("processedCount 应统计已处理结果数量");
}

if (progressPercent(sampleMetrics) !== 80) {
  throw new Error("progressPercent 应返回整数百分比");
}

if (progressPercent({ ...sampleMetrics, total_count: 0 }) !== 0) {
  throw new Error("总数为 0 时进度应为 0%");
}
