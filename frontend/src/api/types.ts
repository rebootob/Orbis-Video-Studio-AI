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
  | 'IMAGES_IN_PROGRESS'
  | 'IMAGES_GENERATED'
  | 'IMAGES_APPROVED'
  | 'VIDEO_IN_PROGRESS'
  | 'FINAL_REVIEW'
  | 'AUDIO_PLAN_GENERATED'
  | 'AUDIO_PLAN_APPROVED'
  | 'AUDIO_IN_PROGRESS'
  | 'AUDIO_MIX_READY'
  | 'AUDIO_APPROVED'
  | 'READY_FOR_ASSEMBLY'
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
  automation_mode?: AutomationMode;
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
  keyframe_asset_id?: string | null;
  keyframe_url?: string | null;
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
  job_type?: string;
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
  operation_type?: 'CONTINUE_INCOMPLETE' | 'RETRY_FAILED' | 'GENERATE_SELECTED';
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
  decision: 'QUEUED' | 'SKIPPED' | 'FAILED';
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

export type AutomationMode = 'MANUAL' | 'ASSISTED' | 'AUTO';

export type OrchestrationActionType =
  | 'GENERATION'
  | 'APPROVAL'
  | 'REVISION'
  | 'EXECUTION'
  | 'RECOVERY'
  | 'NAVIGATION';

export type OrchestrationActionResult =
  | 'APPLIED'
  | 'NO_OP'
  | 'BLOCKED'
  | 'REJECTED'
  | 'FAILED';

export interface OrchestrationActionModel {
  action: string;
  display_name: string;
  description: string;
  action_type: OrchestrationActionType;
  is_chargeable: boolean;
  is_blocked: boolean;
  blocked_reason?: string | null;
  parameters?: Record<string, any> | null;
}

export interface OrchestrationStateResponse {
  project_id: string;
  current_stage: string;
  video_mode: string;
  automation_mode: AutomationMode;
  stage_display_name: string;
  stage_description: string;
  is_approval_required: boolean;
  is_blocked: boolean;
  blocked_reasons: string[];
  recommended_action?: OrchestrationActionModel | null;
  available_actions: OrchestrationActionModel[];
  summary: Record<string, any>;
}

export interface OrchestrationAuditResponse {
  id: string;
  project_id: string;
  from_state: string;
  to_state?: string | null;
  action: string;
  actor: string;
  result: string;
  reason_code?: string | null;
  detail?: string | null;
  created_at: string;
}

export interface OrchestrationHistoryResponse {
  total: number;
  limit: number;
  offset: number;
  items: OrchestrationAuditResponse[];
}

export interface ExecuteActionPayload {
  action: string;
  parameters?: Record<string, any>;
}

export interface ExecuteActionResponse {
  success: boolean;
  action: string;
  from_stage: string;
  to_stage: string;
  result: OrchestrationActionResult;
  message: string;
  audit_id?: string | null;
  orchestration_state: OrchestrationStateResponse;
}

export interface ApproveStagePayload {
  stage?: string;
  notes?: string;
}

export interface ApproveStageResponse {
  success: boolean;
  from_stage: string;
  to_stage: string;
  result: OrchestrationActionResult;
  message: string;
  audit_id?: string | null;
  orchestration_state: OrchestrationStateResponse;
}

export interface OrchestrationSettingsPayload {
  automation_mode: AutomationMode;
}

export interface AudioClip {
  id: string;
  project_id: string;
  scene_id?: string | null;
  shot_id?: string | null;
  video_asset_id?: string | null;
  asset_id?: string | null;
  audio_type: 'ORIGINAL_AUDIO' | 'VO' | 'DIALOGUE' | 'BGM' | 'SFX' | 'AMBIENCE';
  source_type: string;
  generation_mode: string;
  scope: string;
  name: string;
  prompt?: string | null;
  start_time: number;
  duration_seconds?: number | null;
  volume: number;
  mute: boolean;
  fade_in: number;
  fade_out: number;
  ducking_role: string;
  ducking_amount_db: number;
  speaker?: string | null;
  language?: string | null;
  is_locked: boolean;
  status: string;
  version: number;
  provenance?: Record<string, any> | null;
  updated_at?: string | null;
}

export interface AudioPlan {
  id: string;
  project_id: string;
  status: string;
  version: number;
  plan_data?: Record<string, any> | null;
  updated_at?: string | null;
}

export interface PaginatedAudioClipsResponse {
  items: AudioClip[];
  total: number;
  limit: number;
  offset: number;
}
