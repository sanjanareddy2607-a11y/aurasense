export type Role = 'individual' | 'researcher' | 'admin'

export interface Profile {
  display_name: string | null
  organisation: string | null
  share_aggregate: boolean
  store_raw_signals: boolean
  allow_baseline: boolean
  baseline_min_sessions: number
  data_note: string | null
}

export interface User {
  id: string
  name: string
  email: string
  role: Role
  status: string
  is_demo: boolean
  created_at: string
  profile: Profile
}

export interface QualityIssue {
  code: string
  severity: string
  message: string
}

export interface Quality {
  score: number | null
  grade: string | null
  issues: QualityIssue[]
}

export interface LocalContribution {
  feature: string
  label: string
  unit: string
  group: string
  value: number
  reference_median: number
  contribution: number
  direction: string
}

export interface Explanation {
  method?: string
  method_label?: string
  note?: string
  global_top?: { feature: string; importance: number; share: number }[]
  local?: LocalContribution[]
  reference?: Record<string, { p10: number; p50: number; p90: number; mean: number; std: number }>
}

export interface Analysis {
  id: string
  user_id: string
  session_id: string | null
  dataset_id: string | null
  title: string
  source_type: string
  source_label: string
  model_version: string
  predicted_class: 'neutral' | 'stress' | 'amusement' | null
  predicted_label: string
  confidence: number | null
  uncertainty: number | null
  stress_score: number | null
  class_probabilities: Record<string, number>
  quality: Quality
  imputed_features: string[]
  explanation: Explanation
  window_count: number
  duration_seconds: number
  notes: string | null
  is_demo: boolean
  created_at: string
  features?: Record<string, number | null>
  dataset?: Dataset
  session?: {
    id: string
    scenario: string
    is_simulation: boolean
    duration_seconds: number
    status: string
  }
}

export interface Session {
  id: string
  started_at: string
  ended_at: string | null
  data_source: string
  scenario: string
  status: string
  is_simulation: boolean
  is_demo: boolean
  duration_seconds: number
  quality_score: number | null
  quality_grade: string | null
  latest_analysis?: Analysis | null
}

export interface Scenario {
  key: string
  label: string
  description: string
  expected_pattern: string
  is_simulation?: boolean
}

export interface LivePrediction {
  available: boolean
  predicted_class: string | null
  predicted_label: string
  confidence: number | null
  uncertainty?: number | null
  stress_probability: number | null
  class_probabilities: Record<string, number>
  quality: Quality
  status: string
  message?: string | null
  windows_used?: number
  limitations?: string[]
  explanation?: Explanation
  stress_score?: number | null
}

export interface TickResponse {
  status: string
  elapsed_seconds: number
  scenario: string
  scenario_label?: string
  is_simulation: boolean
  signal?: {
    ecg: (number | null)[]
    eda: (number | null)[]
    resp: (number | null)[]
    motion: (number | null)[]
    ecg_sampling_rate: number
  }
  hr_series?: { t: number; bpm: number }[]
  prediction: LivePrediction | null
  prediction_history: {
    at_seconds: number
    label: string
    predicted_class: string | null
    confidence: number | null
    stress_probability: number | null
    quality_score: number
    timestamp: string
  }[]
  quality?: Quality
  duration_seconds?: number
}

export interface BaselineFeature {
  mean: number
  std: number
  min: number
  max: number
  n: number
  label: string
  unit: string
  group: string
}

export interface BaselinePayload {
  baseline: {
    exists: boolean
    id?: string
    session_count: number
    required_sessions: number
    reliable: boolean
    reliability: string
    message: string
    updated_at?: string | null
    version?: number | null
    enabled?: boolean
    features: Record<string, BaselineFeature>
    trend: {
      id: string
      created_at: string | null
      stress_probability: number | null
      hr_mean: number | null
      eda_mean: number | null
      rmssd: number | null
      quality: number | null
    }[]
    disclaimer: string
  }
  latest_comparison: {
    available: boolean
    comparisons: {
      feature: string
      label: string
      unit: string
      value: number
      baseline_mean: number
      z_score: number
      direction: string
    }[]
    notable: {
      feature: string
      label: string
      unit: string
      value: number
      baseline_mean: number
      z_score: number
      direction: string
    }[]
    summary: string
    analysis_id?: string
    analysis_title?: string
  } | null
  eligible_analyses: number
  notice: string
}

export interface Dataset {
  id: string
  name: string
  source: string
  description: string | null
  channels: string[] | Record<string, string[]>
  sampling_rates: Record<string, number>
  participant_count: number
  label_distribution: Record<string, number>
  class_names: string[]
  is_demo: boolean
  is_reference: boolean
  uploaded_by: string | null
  created_at: string
  file_meta?: Record<string, unknown>
}

export interface Inspection {
  filename: string
  size_bytes: number
  rows: number
  columns: string[]
  column_count: number
  channels: { key: string; label: string; column: string }[]
  sampling_rate: number
  sampling_rate_source: string
  duration_seconds: number
  n_samples: number
  windows: number
  missing_values: Record<string, number>
  quality: Quality
  preview: Record<string, (number | null)[]>
  preview_seconds: number
  unrecognised_columns: string[]
}

export interface ExperimentMetrics {
  accuracy: number
  balanced_accuracy: number
  precision_macro: number
  recall_macro: number
  f1_macro: number
  f1_weighted: number
  confusion_matrix: number[][]
  per_class: Record<string, { precision: number; recall: number; f1: number; support: number }>
  n_test_windows: number
  balanced_accuracy_std?: number
}

export interface ModelResult {
  model: string
  metrics: ExperimentMetrics
  per_subject: Record<string, { accuracy: number; balanced_accuracy: number; windows: number }>
  mean_subject_balanced_accuracy: number
}

export interface Experiment {
  id: string
  dataset_id: string | null
  model_type: string
  evaluation_strategy: string
  metrics: Record<string, unknown>
  model_version: string
  notes: string | null
  created_at: string
}

export interface ResearchOverview {
  dataset: Dataset | null
  dataset_summary: {
    participants?: string[]
    participant_count?: number
    windows?: number
    class_distribution?: Record<string, number>
    class_distribution_by_subject?: Record<string, Record<string, number>>
    channels?: Record<string, string[]>
    sampling_rates?: Record<string, number>
    window_seconds?: number
    step_seconds?: number
    label_mapping?: Record<string, string>
    excluded_labels?: string
    missing_feature_percent?: Record<string, number>
  } | null
  metrics: {
    models: ModelResult[]
    best_model: string
    best_model_version: string
    evaluation_strategy: string
    limitations: string[]
    feature_importance: { feature: string; importance: number; share: number }[]
    classes: string[]
    windows: number
    participants: number
    class_distribution: Record<string, number>
    generated_at: string
  } | null
  model: {
    available: boolean
    name?: string
    version?: string
    trained_at?: string
    cv_strategy?: string
    training_windows?: number
    participants?: string[]
    global_metrics?: ExperimentMetrics
    feature_importance?: { feature: string; importance: number; share: number }[]
  }
  features: { name: string; label?: string; unit?: string; group?: string }[]
  experiments: Experiment[]
  can_run_experiments: boolean
  availability: { feature_table: boolean; trained_model: boolean }
  citation: string
  dataset_url: string
  paper_url: string
}

export interface InstitutionOverview {
  generated_at: string
  window_weeks: number
  min_cohort: number
  summary: {
    sessions: number
    participants: number
    consenting_users: number
    mean_stress_probability: number | null
    mean_quality: number | null
    demo_sessions: number
  }
  weekly: {
    week_start: string
    sessions: number
    participants: number
    mean_stress_probability: number | null
    stress_share: number
    neutral_share: number
    amusement_share: number
    mean_quality: number | null
    mean_confidence: number | null
    demo_sessions: number
  }[]
  class_distribution: Record<string, { count: number; share: number }>
  sources: Record<string, number>
  privacy: {
    suppressed_groups: number
    min_sessions_per_group: number
    min_participants_per_group: number
    opted_in: boolean
    note: string
    demo_data_included: boolean
  }
  disclaimer: string
}

export interface ReportRecord {
  id: string
  kind: string
  title: string
  analysis_id: string | null
  experiment_id: string | null
  meta: Record<string, unknown>
  has_file: boolean
  created_at: string
}
