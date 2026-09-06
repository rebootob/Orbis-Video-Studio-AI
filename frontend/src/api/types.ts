export type VideoMode = 'STORY' | 'SHORT' | 'LOOP' | 'SCENE';

export type ShotType =
  | 'AI_GENERATED'
  | 'IMPORTED_VIDEO'
  | 'IMPORTED_IMAGE'
  | 'RECORDED_FOOTAGE'
  | 'STOCK_ASSET'
  | 'MIXED';

export type ApprovalStatus =
  | 'DRAFT'
  | 'STORY_GENERATED'
  | 'STORY_APPROVED'
  | 'STORYBOARD_GENERATED'
  | 'STORYBOARD_APPROVED'
  | 'SHOT_PLAN_GENERATED'
  | 'SHOT_PLAN_APPROVED'
  | 'IMAGES_GENERATED'
  | 'VIDEO_IN_PROGRESS'
  | 'FINAL_REVIEW'
  | 'APPROVED'
  | 'COMPLETED'
  | 'ARCHIVED';

export type JobStatus =
  | 'PENDING'
  | 'CLAIMED'
  | 'SUBMITTED'
  | 'POLLING'
  | 'COMPLETED'
  | 'FAILED'
  | 'CANCELLED'
  | 'RECONCILIATION_REQUIRED';

export interface Project {
  id: string;
  title: string;
  description?: string | null;
  status: string;
  video_mode: VideoMode;
  purpose?: string | null;
  target_platform?: string | null;
  target_duration_seconds?: number | null;
  preferred_aspect_ratio?: string | null;
  mode_config?: Record<string, any> | null;
  default_config?: Record<string, any> | null;
  budget_limit?: number | null;
  budget_currency?: string;
  budget_threshold_percentage?: number | null;
  scene_count?: number;
  shot_count?: number;
  thumbnail_url?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectCreatePayload {
  title: string;
  description?: string;
  video_mode: VideoMode;
  purpose?: string;
  target_platform?: string;
  target_duration_seconds?: number;
  preferred_aspect_ratio?: string;
  mode_config?: Record<string, any>;
  default_config?: Record<string, any>;
}

export interface ProjectUpdatePayload {
  title?: string;
  description?: string;
  status?: string;
  purpose?: string;
  target_platform?: string;
  target_duration_seconds?: number;
  preferred_aspect_ratio?: string;
  mode_config?: Record<string, any>;
  default_config?: Record<string, any>;
}

export interface Shot {
  id: string;
  scene_id: string;
  shot_number: number;
  shot_type: ShotType;
  source_asset_id?: string | null;
  source_metadata?: Record<string, any> | null;
  provider_config?: Record<string, any> | null;
  visual_prompt?: string | null;
  image_prompt?: string | null;
  video_prompt?: string | null;
  camera?: string | null;
  subject?: string | null;
  action?: string | null;
  duration_seconds: number;
  is_locked: boolean;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface Scene {
  id: string;
  project_id?: string | null;
  story_id?: string | null;
  scene_number: number;
  heading?: string | null;
  description?: string | null;
  purpose?: string | null;
  setting?: string | null;
  duration_seconds?: number | null;
  narration?: string | null;
  dialogue?: any;
  scene_config?: Record<string, any> | null;
  is_locked: boolean;
  created_at: string;
  updated_at: string;
  shots?: Shot[];
}

export interface Story {
  id: string;
  project_id: string;
  title: string;
  logline?: string | null;
  synopsis?: string | null;
  theme?: string | null;
  tone?: string | null;
  target_duration_seconds?: number | null;
  language?: string | null;
  status?: string;
  is_locked: boolean;
  created_at: string;
  updated_at: string;
  scenes?: Scene[];
}

export interface GenerationJob {
  id: string;
  shot_id: string;
  provider_name: string;
  status: JobStatus;
  provider_job_id?: string | null;
  result_video_url?: string | null;
  error_message?: string | null;
  retries: number;
  max_retries: number;
  created_at: string;
  updated_at: string;
}

export interface BudgetSummary {
  project_id: string;
  budget_limit?: number | null;
  currency: string;
  threshold_percentage?: number | null;
  confirmed_cost: number;
  estimated_cost: number;
  total_committed_cost: number;
  remaining_budget?: number | null;
  soft_limit_exceeded: boolean;
  hard_limit_exceeded: boolean;
  has_unknown_costs: boolean;
}

export interface CostLedgerEntry {
  id: string;
  project_id: string;
  shot_id?: string | null;
  job_id?: string | null;
  provider: string;
  operation: string;
  model?: string | null;
  usage_units?: number | null;
  estimated_cost?: number | null;
  actual_cost?: number | null;
  currency: string;
  cost_status: 'ESTIMATED' | 'CONFIRMED' | 'ADJUSTED' | 'UNKNOWN';
  created_at: string;
}

export interface AssetLock {
  id: string;
  project_id: string;
  entity_type: string;
  entity_id: string;
  is_locked: boolean;
  lock_actor?: string | null;
  lock_reason?: string | null;
  locked_at?: string | null;
}

export interface ReferenceItem {
  id: string;
  project_id: string;
  name: string;
  reference_type: 'CHARACTER' | 'LOCATION' | 'STYLE' | 'BRAND' | 'DOCUMENT';
  description?: string | null;
  visual_traits?: Record<string, any> | null;
  is_locked?: boolean;
}

export interface BatchJobEstimateResponse {
  shot_count: number;
  skipped_count?: number;
  total_evaluated?: number;
  estimated_cost_total?: number | null;
  currency: string;
  has_unknown_pricing: boolean;
  warning_messages: string[];
}

export interface BatchJobCreatePayload {
  shot_ids?: string[] | null;
  provider_name?: string | null;
  only_incomplete?: boolean;
}

export interface BatchResumePayload {
  operation_type: 'CONTINUE_INCOMPLETE' | 'RETRY_FAILED' | 'GENERATE_SELECTED';
  shot_ids?: string[] | null;
  provider_name?: string | null;
  only_incomplete?: boolean;
}

export interface BatchRunItem {
  id: string;
  batch_run_id: string;
  shot_id: string;
  job_id?: string | null;
  decision: 'QUEUED' | 'SKIPPED';
  skip_reason?: string | null;
  created_at: string;
}

export interface BatchRun {
  id: string;
  project_id: string;
  operation_type: string;
  status: string;
  requested_count: number;
  eligible_count: number;
  queued_count: number;
  skipped_count: number;
  completed_count: number;
  failed_count: number;
  created_at: string;
  updated_at: string;
  items?: BatchRunItem[];
}

export interface ReorderItem {
  id: string;
  order: number;
}

export interface ReorderPayload {
  items: ReorderItem[];
}

export interface AssetUploadResponse {
  id: string;
  project_id?: string | null;
  asset_type: string;
  original_filename: string;
  file_path: string;
  file_size_bytes?: number | null;
  mime_type?: string | null;
  created_at: string;
}
