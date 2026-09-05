import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict


# --- Project Reference Schemas ---
class ProjectReferenceCreate(BaseModel):
    name: str
    category: str
    description: Optional[str] = None
    reference_asset_id: Optional[uuid.UUID] = None
    is_locked: bool = False
    metadata_json: Optional[Dict[str, Any]] = None


class ProjectReferenceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    reference_asset_id: Optional[uuid.UUID] = None
    is_locked: Optional[bool] = None
    metadata_json: Optional[Dict[str, Any]] = None


class ProjectReferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    category: str
    description: Optional[str] = None
    reference_asset_id: Optional[uuid.UUID] = None
    is_locked: bool
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


# --- Character Bible Schemas ---
class CharacterBibleCreate(BaseModel):
    name: str
    role: Optional[str] = None
    description: Optional[str] = None
    appearance: Optional[str] = None
    wardrobe: Optional[str] = None
    age_range: Optional[str] = None
    gender_presentation: Optional[str] = None
    nationality_cultural_context: Optional[str] = None
    personality: Optional[str] = None
    speaking_style: Optional[str] = None
    continuity_notes: Optional[str] = None
    reference_asset_id: Optional[uuid.UUID] = None
    is_locked: bool = False


class CharacterBibleUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    description: Optional[str] = None
    appearance: Optional[str] = None
    wardrobe: Optional[str] = None
    age_range: Optional[str] = None
    gender_presentation: Optional[str] = None
    nationality_cultural_context: Optional[str] = None
    personality: Optional[str] = None
    speaking_style: Optional[str] = None
    continuity_notes: Optional[str] = None
    reference_asset_id: Optional[uuid.UUID] = None
    is_locked: Optional[bool] = None


class CharacterBibleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    role: Optional[str] = None
    description: Optional[str] = None
    appearance: Optional[str] = None
    wardrobe: Optional[str] = None
    age_range: Optional[str] = None
    gender_presentation: Optional[str] = None
    nationality_cultural_context: Optional[str] = None
    personality: Optional[str] = None
    speaking_style: Optional[str] = None
    continuity_notes: Optional[str] = None
    reference_asset_id: Optional[uuid.UUID] = None
    is_locked: bool
    created_at: datetime
    updated_at: datetime


# --- Location Bible Schemas ---
class LocationBibleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    environment: Optional[str] = None
    visual_features: Optional[str] = None
    lighting: Optional[str] = None
    time_of_day_default: Optional[str] = None
    continuity_notes: Optional[str] = None
    reference_asset_id: Optional[uuid.UUID] = None
    is_locked: bool = False


class LocationBibleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    environment: Optional[str] = None
    visual_features: Optional[str] = None
    lighting: Optional[str] = None
    time_of_day_default: Optional[str] = None
    continuity_notes: Optional[str] = None
    reference_asset_id: Optional[uuid.UUID] = None
    is_locked: Optional[bool] = None


class LocationBibleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    description: Optional[str] = None
    environment: Optional[str] = None
    visual_features: Optional[str] = None
    lighting: Optional[str] = None
    time_of_day_default: Optional[str] = None
    continuity_notes: Optional[str] = None
    reference_asset_id: Optional[uuid.UUID] = None
    is_locked: bool
    created_at: datetime
    updated_at: datetime


# --- Style Bible Schemas ---
class StyleBibleCreate(BaseModel):
    name: str
    visual_style: Optional[str] = None
    camera_style: Optional[str] = None
    color_direction: Optional[str] = None
    lighting_style: Optional[str] = None
    composition_rules: Optional[str] = None
    realism_level: Optional[str] = None
    negative_constraints: Optional[str] = None
    reference_asset_id: Optional[uuid.UUID] = None
    is_locked: bool = False


class StyleBibleUpdate(BaseModel):
    name: Optional[str] = None
    visual_style: Optional[str] = None
    camera_style: Optional[str] = None
    color_direction: Optional[str] = None
    lighting_style: Optional[str] = None
    composition_rules: Optional[str] = None
    realism_level: Optional[str] = None
    negative_constraints: Optional[str] = None
    reference_asset_id: Optional[uuid.UUID] = None
    is_locked: Optional[bool] = None


class StyleBibleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    visual_style: Optional[str] = None
    camera_style: Optional[str] = None
    color_direction: Optional[str] = None
    lighting_style: Optional[str] = None
    composition_rules: Optional[str] = None
    realism_level: Optional[str] = None
    negative_constraints: Optional[str] = None
    reference_asset_id: Optional[uuid.UUID] = None
    is_locked: bool
    created_at: datetime
    updated_at: datetime


# --- Brand Bible Schemas ---
class BrandBibleCreate(BaseModel):
    brand_name: str
    brand_colors: Optional[str] = None
    typography_notes: Optional[str] = None
    do_and_dont_rules: Optional[str] = None
    tone: Optional[str] = None
    mandatory_wording: Optional[str] = None
    continuity_notes: Optional[str] = None
    logo_asset_id: Optional[uuid.UUID] = None
    is_locked: bool = False


class BrandBibleUpdate(BaseModel):
    brand_name: Optional[str] = None
    brand_colors: Optional[str] = None
    typography_notes: Optional[str] = None
    do_and_dont_rules: Optional[str] = None
    tone: Optional[str] = None
    mandatory_wording: Optional[str] = None
    continuity_notes: Optional[str] = None
    logo_asset_id: Optional[uuid.UUID] = None
    is_locked: Optional[bool] = None


class BrandBibleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    brand_name: str
    brand_colors: Optional[str] = None
    typography_notes: Optional[str] = None
    do_and_dont_rules: Optional[str] = None
    tone: Optional[str] = None
    mandatory_wording: Optional[str] = None
    continuity_notes: Optional[str] = None
    logo_asset_id: Optional[uuid.UUID] = None
    is_locked: bool
    created_at: datetime
    updated_at: datetime
