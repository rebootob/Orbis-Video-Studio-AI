import type {
  Project,
  PaginatedAudioClipsResponse,
  ProjectCreatePayload,
  ProjectUpdatePayload,
  Scene,
  Shot,
  Story,
  GenerationJob,
  BudgetSummary,
  CostLedgerEntry,
  AssetLock,
  ReferenceItem,
  BatchJobEstimateResponse,
  BatchJobCreatePayload,
  BatchResumePayload,
  BatchRun,
  ReorderItem,
  AssetUploadResponse,
  OrchestrationStateResponse,
  OrchestrationHistoryResponse,
  ExecuteActionPayload,
  ExecuteActionResponse,
  ApproveStagePayload,
  ApproveStageResponse,
  OrchestrationSettingsPayload,
  AudioClip,
  AudioPlan,
  AssemblyTimeline,
  AssemblyShotPlacement,
  TimelineCheckpoint,
  AssemblyBlocker,
  QCRun,
  QCSimpleSummary,
  QCHistoryResponse,
  WarningDecision,
  WarningDecisionType,
  ApprovalRecord,
} from './types';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${BASE_URL}${endpoint}`;
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  const response = await fetch(url, { ...options, headers });

  if (response.status === 204) {
    return {} as T;
  }

  if (!response.ok) {
    let errorDetail = `Request failed with status ${response.status}`;
    try {
      const errorJson = await response.json();
      errorDetail = errorJson.detail || errorDetail;
    } catch {
      // ignore json parse error
    }
    throw new Error(errorDetail);
  }

  return response.json();
}

export const api = {
  // Projects
  async listProjects(includeArchived = false): Promise<Project[]> {
    return request<Project[]>(`/projects?include_archived=${includeArchived}`);
  },

  async getProject(projectId: string): Promise<Project> {
    return request<Project>(`/projects/${projectId}`);
  },

  async createProject(payload: ProjectCreatePayload): Promise<Project> {
    return request<Project>('/projects', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async updateProject(projectId: string, payload: ProjectUpdatePayload): Promise<Project> {
    return request<Project>(`/projects/${projectId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  },

  async deleteProject(projectId: string): Promise<Project> {
    // Soft-archive project to retain full history
    return request<Project>(`/projects/${projectId}`, {
      method: 'DELETE',
    });
  },

  async archiveProject(projectId: string): Promise<Project> {
    return request<Project>(`/projects/${projectId}/archive`, {
      method: 'POST',
    });
  },

  async unarchiveProject(projectId: string): Promise<Project> {
    return request<Project>(`/projects/${projectId}/unarchive`, {
      method: 'POST',
    });
  },

  async duplicateProject(projectId: string): Promise<Project> {
    return request<Project>(`/projects/${projectId}/duplicate`, {
      method: 'POST',
    });
  },

  // Scenes
  async listProjectScenes(projectId: string): Promise<Scene[]> {
    return request<Scene[]>(`/projects/${projectId}/scenes`);
  },

  async createScene(projectId: string, payload: Partial<Scene>): Promise<Scene> {
    return request<Scene>(`/projects/${projectId}/scenes`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async updateScene(sceneId: string, payload: Partial<Scene>): Promise<Scene> {
    return request<Scene>(`/scenes/${sceneId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  },

  async deleteScene(sceneId: string): Promise<void> {
    return request<void>(`/scenes/${sceneId}`, {
      method: 'DELETE',
    });
  },

  async duplicateScene(sceneId: string): Promise<Scene> {
    return request<Scene>(`/scenes/${sceneId}/duplicate`, {
      method: 'POST',
    });
  },

  async reorderScenes(projectId: string, items: ReorderItem[]): Promise<Scene[]> {
    return request<Scene[]>(`/projects/${projectId}/scenes/reorder`, {
      method: 'PATCH',
      body: JSON.stringify({ items }),
    });
  },

  // Shots
  async listSceneShots(sceneId: string): Promise<Shot[]> {
    return request<Shot[]>(`/scenes/${sceneId}/shots`);
  },

  async getShot(shotId: string): Promise<Shot> {
    return request<Shot>(`/shots/${shotId}`);
  },

  async createShot(sceneId: string, payload: Partial<Shot>): Promise<Shot> {
    return request<Shot>(`/scenes/${sceneId}/shots`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async updateShot(shotId: string, payload: Partial<Shot>): Promise<Shot> {
    return request<Shot>(`/shots/${shotId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  },

  async deleteShot(shotId: string): Promise<void> {
    return request<void>(`/shots/${shotId}`, {
      method: 'DELETE',
    });
  },

  async reorderShots(sceneId: string, items: ReorderItem[]): Promise<Shot[]> {
    return request<Shot[]>(`/scenes/${sceneId}/shots/reorder`, {
      method: 'PATCH',
      body: JSON.stringify({ items }),
    });
  },

  async getEffectiveShotConfig(shotId: string): Promise<any> {
    return request<any>(`/shots/${shotId}/effective-config`);
  },

  // Story Generation (Automation)
  async getProjectStory(projectId: string): Promise<Story | null> {
    try {
      return await request<Story>(`/projects/${projectId}/story`);
    } catch {
      return null;
    }
  },

  async generateProjectStory(
    projectId: string,
    options?: { generate_scenes?: boolean; custom_instructions?: string }
  ): Promise<Story> {
    return request<Story>(`/projects/${projectId}/story/generate`, {
      method: 'POST',
      body: JSON.stringify(options || {}),
    });
  },

  async generateStoryScenes(
    storyId: string,
    options?: { generate_shots?: boolean; custom_instructions?: string }
  ): Promise<Scene[]> {
    return request<Scene[]>(`/stories/${storyId}/scenes/generate`, {
      method: 'POST',
      body: JSON.stringify(options || {}),
    });
  },

  async generateProjectStoryboard(
    projectId: string,
    options?: { generate_shots?: boolean; custom_instructions?: string }
  ): Promise<Scene[]> {
    return request<Scene[]>(`/projects/${projectId}/storyboard/generate`, {
      method: 'POST',
      body: JSON.stringify(options || {}),
    });
  },

  async generateSceneShots(
    sceneId: string,
    options?: { custom_instructions?: string }
  ): Promise<Shot[]> {
    return request<Shot[]>(`/scenes/${sceneId}/shots/generate`, {
      method: 'POST',
      body: JSON.stringify(options || {}),
    });
  },

  // Generation Queue / Jobs
  async listProjectJobs(projectId: string): Promise<GenerationJob[]> {
    return request<GenerationJob[]>(`/projects/${projectId}/jobs`);
  },

  async listShotJobs(shotId: string): Promise<GenerationJob[]> {
    return request<GenerationJob[]>(`/shots/${shotId}/jobs`);
  },

  async createJob(shotId: string, providerName?: string): Promise<GenerationJob> {
    return request<GenerationJob>('/jobs', {
      method: 'POST',
      body: JSON.stringify({
        shot_id: shotId,
        provider_name: providerName || undefined,
      }),
    });
  },

  async estimateBatchJobs(projectId: string, payload?: BatchJobCreatePayload): Promise<BatchJobEstimateResponse> {
    return request<BatchJobEstimateResponse>(`/projects/${projectId}/jobs/estimate`, {
      method: 'POST',
      body: JSON.stringify(payload || {}),
    });
  },

  async batchGenerateProjectShots(projectId: string, payload?: BatchJobCreatePayload): Promise<GenerationJob[]> {
    return request<GenerationJob[]>(`/projects/${projectId}/jobs/batch`, {
      method: 'POST',
      body: JSON.stringify(payload || {}),
    });
  },

  async resumeProjectJobs(projectId: string, payload?: BatchResumePayload): Promise<BatchRun> {
    return request<BatchRun>(`/projects/${projectId}/jobs/resume`, {
      method: 'POST',
      body: JSON.stringify(payload || {}),
    });
  },

  async listBatchRuns(projectId: string): Promise<BatchRun[]> {
    return request<BatchRun[]>(`/projects/${projectId}/batch-runs`);
  },

  async getBatchRun(projectId: string, runId: string): Promise<BatchRun> {
    return request<BatchRun>(`/projects/${projectId}/batch-runs/${runId}`);
  },

  async cancelJob(jobId: string): Promise<GenerationJob> {
    return request<GenerationJob>(`/jobs/${jobId}/cancel`, {
      method: 'POST',
    });
  },

  async pollJob(jobId: string): Promise<GenerationJob> {
    return request<GenerationJob>(`/jobs/${jobId}/poll`, {
      method: 'POST',
    });
  },

  // Budget & Cost Ledger
  async getProjectBudget(projectId: string): Promise<BudgetSummary> {
    return request<BudgetSummary>(`/projects/${projectId}/budget`);
  },

  async updateProjectBudget(
    projectId: string,
    limit?: number | null,
    currency = 'USD',
    thresholdPercentage = 80.0
  ): Promise<BudgetSummary> {
    return request<BudgetSummary>(`/projects/${projectId}/budget`, {
      method: 'PUT',
      body: JSON.stringify({
        budget_limit: limit,
        budget_currency: currency,
        budget_threshold_percentage: thresholdPercentage,
      }),
    });
  },

  async listProjectLedger(projectId: string): Promise<CostLedgerEntry[]> {
    return request<CostLedgerEntry[]>(`/projects/${projectId}/costs/ledger`);
  },

  // Locks
  async listProjectLocks(projectId: string): Promise<AssetLock[]> {
    return request<AssetLock[]>(`/projects/${projectId}/locks`);
  },

  async lockEntity(
    projectId: string,
    entityType: string,
    entityId: string,
    actor = 'workspace_user',
    reason = 'User locked from workspace'
  ): Promise<AssetLock> {
    return request<AssetLock>('/locks/lock', {
      method: 'POST',
      body: JSON.stringify({
        project_id: projectId,
        entity_type: entityType,
        entity_id: entityId,
        actor,
        reason,
      }),
    });
  },

  async unlockEntity(
    projectId: string,
    entityType: string,
    entityId: string,
    actor = 'workspace_user',
    reason = 'User unlocked from workspace'
  ): Promise<AssetLock> {
    return request<AssetLock>('/locks/unlock', {
      method: 'POST',
      body: JSON.stringify({
        project_id: projectId,
        entity_type: entityType,
        entity_id: entityId,
        actor,
        reason,
      }),
    });
  },

  // Reference Library
  async listProjectReferences(projectId: string): Promise<ReferenceItem[]> {
    const [characters, locations, styles, brands] = await Promise.allSettled([
      request<any[]>(`/projects/${projectId}/characters`),
      request<any[]>(`/projects/${projectId}/locations`),
      request<any[]>(`/projects/${projectId}/styles`),
      request<any[]>(`/projects/${projectId}/brands`),
    ]);

    const results: ReferenceItem[] = [];

    if (characters.status === 'fulfilled' && Array.isArray(characters.value)) {
      results.push(...characters.value.map(c => ({
        id: c.id,
        project_id: projectId,
        name: c.name,
        reference_type: 'CHARACTER' as const,
        description: c.backstory || c.description,
        is_locked: c.is_locked,
      })));
    }
    if (locations.status === 'fulfilled' && Array.isArray(locations.value)) {
      results.push(...locations.value.map(l => ({
        id: l.id,
        project_id: projectId,
        name: l.name,
        reference_type: 'LOCATION' as const,
        description: l.setting_notes || l.description,
        is_locked: l.is_locked,
      })));
    }
    if (styles.status === 'fulfilled' && Array.isArray(styles.value)) {
      results.push(...styles.value.map(s => ({
        id: s.id,
        project_id: projectId,
        name: s.name,
        reference_type: 'STYLE' as const,
        description: s.style_prompt_prefix || s.description,
        is_locked: s.is_locked,
      })));
    }
    if (brands.status === 'fulfilled' && Array.isArray(brands.value)) {
      results.push(...brands.value.map(b => ({
        id: b.id,
        project_id: projectId,
        name: b.name,
        reference_type: 'BRAND' as const,
        description: b.guidelines || b.description,
        is_locked: b.is_locked,
      })));
    }

    return results;
  },

  async createCharacter(projectId: string, data: { name: string; backstory?: string }): Promise<any> {
    return request<any>(`/projects/${projectId}/characters`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async createLocation(projectId: string, data: { name: string; setting_notes?: string }): Promise<any> {
    return request<any>(`/projects/${projectId}/locations`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async createStyle(projectId: string, data: { name: string; style_prompt_prefix?: string }): Promise<any> {
    return request<any>(`/projects/${projectId}/styles`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async createBrand(projectId: string, data: { name: string; guidelines?: string }): Promise<any> {
    return request<any>(`/projects/${projectId}/brands`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  // Assets & Documents
  async listProjectAssets(projectId: string): Promise<AssetUploadResponse[]> {
    return request<AssetUploadResponse[]>(`/projects/${projectId}/assets`);
  },

  async uploadAsset(
    projectId: string,
    file: File,
    assetType = 'DOCUMENT',
    name?: string
  ): Promise<AssetUploadResponse> {
    const formData = new FormData();
    formData.append('project_id', projectId);
    formData.append('asset_type', assetType);
    if (name) {
      formData.append('name', name);
    }
    formData.append('file', file);

    const url = `${BASE_URL}/assets/upload`;
    const response = await fetch(url, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      let errorDetail = `Asset upload failed with status ${response.status}`;
      try {
        const errorJson = await response.json();
        errorDetail = errorJson.detail || errorDetail;
      } catch {
        // ignore
      }
      throw new Error(errorDetail);
    }

    return response.json();
  },

  // Production Orchestrator & Staged Approvals
  async getOrchestrationState(projectId: string): Promise<OrchestrationStateResponse> {
    return request<OrchestrationStateResponse>(`/projects/${projectId}/orchestration`);
  },

  async executeOrchestrationAction(
    projectId: string,
    payload: ExecuteActionPayload
  ): Promise<ExecuteActionResponse> {
    return request<ExecuteActionResponse>(`/projects/${projectId}/orchestration/execute`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async approveStage(
    projectId: string,
    payload: ApproveStagePayload = {}
  ): Promise<ApproveStageResponse> {
    return request<ApproveStageResponse>(`/projects/${projectId}/orchestration/approve`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async updateOrchestrationSettings(
    projectId: string,
    payload: OrchestrationSettingsPayload
  ): Promise<OrchestrationStateResponse> {
    return request<OrchestrationStateResponse>(`/projects/${projectId}/orchestration/settings`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  },

  async getOrchestrationHistory(
    projectId: string,
    params: { limit?: number; offset?: number } = {}
  ): Promise<OrchestrationHistoryResponse> {
    const query = new URLSearchParams();
    if (params.limit !== undefined) query.set('limit', String(params.limit));
    if (params.offset !== undefined) query.set('offset', String(params.offset));
    const qs = query.toString();
    return request<OrchestrationHistoryResponse>(
      `/projects/${projectId}/orchestration/history${qs ? `?${qs}` : ''}`
    );
  },

  // Audio Production
  async getAudioPlan(projectId: string): Promise<AudioPlan> {
    return request<AudioPlan>(`/projects/${projectId}/audio/plan`);
  },

  async generateAudioPlan(projectId: string): Promise<AudioPlan> {
    return request<AudioPlan>(`/projects/${projectId}/audio/plan`, {
      method: 'POST',
    });
  },

  async approveAudioPlan(projectId: string): Promise<AudioPlan> {
    return request<AudioPlan>(`/projects/${projectId}/audio/plan/approve`, {
      method: 'POST',
    });
  },

  async listAudioClips(
    projectId: string,
    params: { limit?: number; offset?: number; audio_type?: string; scope?: string } = {}
  ): Promise<PaginatedAudioClipsResponse> {
    const query = new URLSearchParams();
    if (params.limit !== undefined) query.set('limit', String(params.limit));
    if (params.offset !== undefined) query.set('offset', String(params.offset));
    if (params.audio_type) query.set('audio_type', params.audio_type);
    if (params.scope) query.set('scope', params.scope);
    const qs = query.toString();
    return request<PaginatedAudioClipsResponse>(
      `/projects/${projectId}/audio/clips${qs ? `?${qs}` : ''}`
    );
  },

  async lockAudioClip(
    projectId: string,
    clipId: string,
    payload: { actor?: string; reason?: string } = {}
  ): Promise<AudioClip> {
    return request<AudioClip>(`/projects/${projectId}/audio/clips/${clipId}/lock`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async unlockAudioClip(
    projectId: string,
    clipId: string,
    payload: { actor?: string; reason?: string } = {}
  ): Promise<AudioClip> {
    return request<AudioClip>(`/projects/${projectId}/audio/clips/${clipId}/unlock`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async getAudioPlanHistory(
    projectId: string,
    params: { limit?: number; offset?: number } = {}
  ): Promise<{ items: any[]; total: number; limit: number; offset: number }> {
    const query = new URLSearchParams();
    if (params.limit !== undefined) query.set('limit', String(params.limit));
    if (params.offset !== undefined) query.set('offset', String(params.offset));
    const qs = query.toString();
    return request<any>(`/projects/${projectId}/audio/plan/history${qs ? `?${qs}` : ''}`);
  },

  async getAudioClipHistory(
    projectId: string,
    clipId: string,
    params: { limit?: number; offset?: number } = {}
  ): Promise<{ items: any[]; total: number; limit: number; offset: number }> {
    const query = new URLSearchParams();
    if (params.limit !== undefined) query.set('limit', String(params.limit));
    if (params.offset !== undefined) query.set('offset', String(params.offset));
    const qs = query.toString();
    return request<any>(`/projects/${projectId}/audio/clips/${clipId}/history${qs ? `?${qs}` : ''}`);
  },

  async generateClipAudio(
    projectId: string,
    clipId: string,
    payload: { provider_name?: string; cost_authorized?: boolean; actor?: string } = {}
  ): Promise<any> {
    return request<any>(`/projects/${projectId}/audio/clips/${clipId}/generate`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async updateAudioClip(
    projectId: string,
    clipId: string,
    payload: Partial<AudioClip>
  ): Promise<AudioClip> {
    return request<AudioClip>(`/projects/${projectId}/audio/clips/${clipId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  },

  async executeAudioBatch(
    projectId: string,
    payload: { action: string; provider_name?: string; cost_authorized?: boolean; actor?: string }
  ): Promise<any> {
    return request<any>(`/projects/${projectId}/audio/batch`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async computeAudioMix(projectId: string): Promise<any> {
    return request<any>(`/projects/${projectId}/audio/mix`, {
      method: 'POST',
    });
  },

  // Assembly Timeline
  async getAssemblyTimeline(projectId: string): Promise<AssemblyTimeline> {
    return request<AssemblyTimeline>(`/projects/${projectId}/assembly`);
  },

  async autoAssembleTimeline(projectId: string): Promise<AssemblyTimeline> {
    return request<AssemblyTimeline>(`/projects/${projectId}/assembly/auto-assemble`, {
      method: 'POST',
    });
  },

  async updateShotPlacement(projectId: string, placementId: string, payload: any): Promise<AssemblyShotPlacement> {
    return request<AssemblyShotPlacement>(`/projects/${projectId}/assembly/placements/${placementId}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
  },

  async reorderAssemblyScenes(projectId: string, payload: { orders: { scene_id: string; order: number }[] }): Promise<AssemblyTimeline> {
    return request<AssemblyTimeline>(`/projects/${projectId}/assembly/reorder-scenes`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async reorderShotsInScene(projectId: string, sceneId: string, payload: { orders: { shot_id: string; order: number }[] }): Promise<AssemblyTimeline> {
    return request<AssemblyTimeline>(`/projects/${projectId}/assembly/reorder-shots?scene_id=${encodeURIComponent(sceneId)}`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async moveShotToScene(projectId: string, payload: { shot_id: string; target_scene_id: string; target_position: number }): Promise<AssemblyTimeline> {
    return request<AssemblyTimeline>(`/projects/${projectId}/assembly/move-shot`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async createTimelineCheckpoint(projectId: string, payload: { label: string }): Promise<TimelineCheckpoint> {
    return request<TimelineCheckpoint>(`/projects/${projectId}/assembly/checkpoints`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async listTimelineCheckpoints(projectId: string, limit: number = 50, offset: number = 0): Promise<TimelineCheckpoint[]> {
    return request<TimelineCheckpoint[]>(`/projects/${projectId}/assembly/checkpoints?limit=${limit}&offset=${offset}`);
  },

  async restoreTimelineCheckpoint(projectId: string, checkpointId: string): Promise<AssemblyTimeline> {
    return request<AssemblyTimeline>(`/projects/${projectId}/assembly/checkpoints/${checkpointId}/restore`, {
      method: 'POST',
    });
  },

  async getTimelineBlockers(projectId: string): Promise<AssemblyBlocker[]> {
    return request<AssemblyBlocker[]>(`/projects/${projectId}/assembly/blockers`);
  },

  async applyTimelineFix(projectId: string, payload: { blocker_code: string; target_id?: string; fix_code: string }): Promise<any> {
    return request<any>(`/projects/${projectId}/assembly/blockers/apply-fix`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  // QC & Approval Pipeline
  async runQC(projectId: string, actor: string = 'user'): Promise<QCRun> {
    return request<QCRun>(`/projects/${projectId}/qc/run?actor=${encodeURIComponent(actor)}`, {
      method: 'POST',
    });
  },

  async getQCSummary(projectId: string): Promise<QCSimpleSummary> {
    return request<QCSimpleSummary>(`/projects/${projectId}/qc/summary`);
  },

  async getQCHistory(projectId: string, offset: number = 0, limit: number = 20): Promise<QCHistoryResponse> {
    return request<QCHistoryResponse>(`/projects/${projectId}/qc/history?offset=${offset}&limit=${limit}`);
  },

  async getQCRunFindings(projectId: string, runId: string, offset: number = 0, limit: number = 50): Promise<any> {
    return request<any>(`/projects/${projectId}/qc/runs/${runId}/findings?offset=${offset}&limit=${limit}`);
  },

  async recordWarningDecision(
    projectId: string,
    findingId: string,
    decision: WarningDecisionType,
    reason?: string,
    actor: string = 'user'
  ): Promise<WarningDecision> {
    return request<WarningDecision>(
      `/projects/${projectId}/qc/findings/${findingId}/decision?actor=${encodeURIComponent(actor)}`,
      {
        method: 'POST',
        body: JSON.stringify({ decision, reason }),
      }
    );
  },

  async getFindingDecisionHistory(
    projectId: string,
    findingId: string,
    offset: number = 0,
    limit: number = 20
  ): Promise<WarningDecision[]> {
    return request<WarningDecision[]>(
      `/projects/${projectId}/qc/findings/${findingId}/history?offset=${offset}&limit=${limit}`
    );
  },

  async approveProduction(
    projectId: string,
    payload: { timeline_id?: string; qc_run_id?: string; notes?: string } = {},
    actor: string = 'user'
  ): Promise<ApprovalRecord> {
    return request<ApprovalRecord>(
      `/projects/${projectId}/qc/approve?actor=${encodeURIComponent(actor)}`,
      {
        method: 'POST',
        body: JSON.stringify(payload),
      }
    );
  },
};

export const apiClient = api;
