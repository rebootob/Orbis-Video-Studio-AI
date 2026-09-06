import type {
  Project,
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
  async listProjects(): Promise<Project[]> {
    return request<Project[]>('/projects');
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

  async deleteProject(projectId: string): Promise<void> {
    return request<void>(`/projects/${projectId}`, {
      method: 'DELETE',
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

  async generateProjectStory(projectId: string, options?: { custom_instructions?: string }): Promise<Story> {
    return request<Story>(`/projects/${projectId}/story/generate`, {
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

  async createJob(shotId: string, providerName = 'vidu'): Promise<GenerationJob> {
    return request<GenerationJob>('/jobs', {
      method: 'POST',
      body: JSON.stringify({
        shot_id: shotId,
        provider_name: providerName,
      }),
    });
  },

  async batchGenerateProjectShots(projectId: string, providerName = 'vidu'): Promise<GenerationJob[]> {
    return request<GenerationJob[]>(`/projects/${projectId}/jobs/batch?provider_name=${encodeURIComponent(providerName)}`, {
      method: 'POST',
    });
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
};
