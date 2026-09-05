import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.reference_library import (
    ProjectReferenceCreate, ProjectReferenceUpdate, ProjectReferenceResponse,
    CharacterBibleCreate, CharacterBibleUpdate, CharacterBibleResponse,
    LocationBibleCreate, LocationBibleUpdate, LocationBibleResponse,
    StyleBibleCreate, StyleBibleUpdate, StyleBibleResponse,
    BrandBibleCreate, BrandBibleUpdate, BrandBibleResponse,
)
from app.services.reference_library.reference_service import ReferenceService, ReferenceError

router = APIRouter()


def _map_error(e: ReferenceError) -> HTTPException:
    if e.code in ("PROJECT_NOT_FOUND", "REFERENCE_NOT_FOUND", "CHARACTER_NOT_FOUND", "LOCATION_NOT_FOUND", "STYLE_NOT_FOUND", "BRAND_NOT_FOUND"):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    elif e.code in ("INVALID_ASSET_LINK", "INVALID_CATEGORY"):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    elif e.code == "REFERENCE_LOCKED":
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.message)
    else:
        return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.message)


# --- Project References ---
@router.post("/projects/{project_id}/references", response_model=ProjectReferenceResponse, status_code=status.HTTP_201_CREATED)
def create_project_reference(project_id: uuid.UUID, body: ProjectReferenceCreate, db: Session = Depends(get_db)):
    service = ReferenceService(db)
    try:
        return service.create_reference(
            project_id=project_id,
            name=body.name,
            category=body.category,
            description=body.description,
            reference_asset_id=body.reference_asset_id,
            is_locked=body.is_locked,
            metadata_json=body.metadata_json,
        )
    except ReferenceError as e:
        raise _map_error(e)


@router.get("/projects/{project_id}/references", response_model=List[ProjectReferenceResponse])
def list_project_references(project_id: uuid.UUID, category: Optional[str] = Query(None), db: Session = Depends(get_db)):
    service = ReferenceService(db)
    try:
        return service.list_references(project_id=project_id, category=category)
    except ReferenceError as e:
        raise _map_error(e)


@router.get("/references/{reference_id}", response_model=ProjectReferenceResponse)
def get_project_reference(reference_id: uuid.UUID, db: Session = Depends(get_db)):
    service = ReferenceService(db)
    try:
        return service.get_reference(reference_id)
    except ReferenceError as e:
        raise _map_error(e)


@router.patch("/references/{reference_id}", response_model=ProjectReferenceResponse)
def update_project_reference(reference_id: uuid.UUID, body: ProjectReferenceUpdate, db: Session = Depends(get_db)):
    service = ReferenceService(db)
    try:
        return service.update_reference(
            reference_id=reference_id,
            name=body.name,
            description=body.description,
            reference_asset_id=body.reference_asset_id,
            is_locked=body.is_locked,
            metadata_json=body.metadata_json,
        )
    except ReferenceError as e:
        raise _map_error(e)


@router.delete("/references/{reference_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project_reference(reference_id: uuid.UUID, db: Session = Depends(get_db)):
    service = ReferenceService(db)
    try:
        service.delete_reference(reference_id)
    except ReferenceError as e:
        raise _map_error(e)


# --- Character Bibles ---
@router.post("/projects/{project_id}/characters", response_model=CharacterBibleResponse, status_code=status.HTTP_201_CREATED)
def create_character_bible(project_id: uuid.UUID, body: CharacterBibleCreate, db: Session = Depends(get_db)):
    service = ReferenceService(db)
    try:
        return service.create_character(
            project_id=project_id,
            name=body.name,
            role=body.role,
            description=body.description,
            appearance=body.appearance,
            wardrobe=body.wardrobe,
            age_range=body.age_range,
            gender_presentation=body.gender_presentation,
            nationality_cultural_context=body.nationality_cultural_context,
            personality=body.personality,
            speaking_style=body.speaking_style,
            continuity_notes=body.continuity_notes,
            reference_asset_id=body.reference_asset_id,
            is_locked=body.is_locked,
        )
    except ReferenceError as e:
        raise _map_error(e)


@router.get("/projects/{project_id}/characters", response_model=List[CharacterBibleResponse])
def list_character_bibles(project_id: uuid.UUID, db: Session = Depends(get_db)):
    service = ReferenceService(db)
    try:
        return service.list_characters(project_id)
    except ReferenceError as e:
        raise _map_error(e)


@router.get("/characters/{character_id}", response_model=CharacterBibleResponse)
def get_character_bible(character_id: uuid.UUID, db: Session = Depends(get_db)):
    service = ReferenceService(db)
    try:
        return service.get_character(character_id)
    except ReferenceError as e:
        raise _map_error(e)


@router.patch("/characters/{character_id}", response_model=CharacterBibleResponse)
def update_character_bible(character_id: uuid.UUID, body: CharacterBibleUpdate, db: Session = Depends(get_db)):
    service = ReferenceService(db)
    try:
        return service.update_character(
            character_id=character_id,
            name=body.name,
            role=body.role,
            description=body.description,
            appearance=body.appearance,
            wardrobe=body.wardrobe,
            age_range=body.age_range,
            gender_presentation=body.gender_presentation,
            nationality_cultural_context=body.nationality_cultural_context,
            personality=body.personality,
            speaking_style=body.speaking_style,
            continuity_notes=body.continuity_notes,
            reference_asset_id=body.reference_asset_id,
            is_locked=body.is_locked,
        )
    except ReferenceError as e:
        raise _map_error(e)


@router.delete("/characters/{character_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_character_bible(character_id: uuid.UUID, db: Session = Depends(get_db)):
    service = ReferenceService(db)
    try:
        service.delete_character(character_id)
    except ReferenceError as e:
        raise _map_error(e)


# --- Location Bibles ---
@router.post("/projects/{project_id}/locations", response_model=LocationBibleResponse, status_code=status.HTTP_201_CREATED)
def create_location_bible(project_id: uuid.UUID, body: LocationBibleCreate, db: Session = Depends(get_db)):
    service = ReferenceService(db)
    try:
        return service.create_location(
            project_id=project_id,
            name=body.name,
            description=body.description,
            environment=body.environment,
            visual_features=body.visual_features,
            lighting=body.lighting,
            time_of_day_default=body.time_of_day_default,
            continuity_notes=body.continuity_notes,
            reference_asset_id=body.reference_asset_id,
            is_locked=body.is_locked,
        )
    except ReferenceError as e:
        raise _map_error(e)


@router.get("/projects/{project_id}/locations", response_model=List[LocationBibleResponse])
def list_location_bibles(project_id: uuid.UUID, db: Session = Depends(get_db)):
    service = ReferenceService(db)
    try:
        return service.list_locations(project_id)
    except ReferenceError as e:
        raise _map_error(e)


@router.get("/locations/{location_id}", response_model=LocationBibleResponse)
def get_location_bible(location_id: uuid.UUID, db: Session = Depends(get_db)):
    service = ReferenceService(db)
    try:
        return service.get_location(location_id)
    except ReferenceError as e:
        raise _map_error(e)


@router.patch("/locations/{location_id}", response_model=LocationBibleResponse)
def update_location_bible(location_id: uuid.UUID, body: LocationBibleUpdate, db: Session = Depends(get_db)):
    service = ReferenceService(db)
    try:
        return service.update_location(
            location_id=location_id,
            name=body.name,
            description=body.description,
            environment=body.environment,
            visual_features=body.visual_features,
            lighting=body.lighting,
            time_of_day_default=body.time_of_day_default,
            continuity_notes=body.continuity_notes,
            reference_asset_id=body.reference_asset_id,
            is_locked=body.is_locked,
        )
    except ReferenceError as e:
        raise _map_error(e)


@router.delete("/locations/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_location_bible(location_id: uuid.UUID, db: Session = Depends(get_db)):
    service = ReferenceService(db)
    try:
        service.delete_location(location_id)
    except ReferenceError as e:
        raise _map_error(e)


# --- Style Bibles ---
@router.post("/projects/{project_id}/styles", response_model=StyleBibleResponse, status_code=status.HTTP_201_CREATED)
def create_style_bible(project_id: uuid.UUID, body: StyleBibleCreate, db: Session = Depends(get_db)):
    service = ReferenceService(db)
    try:
        return service.create_style(
            project_id=project_id,
            name=body.name,
            visual_style=body.visual_style,
            camera_style=body.camera_style,
            color_direction=body.color_direction,
            lighting_style=body.lighting_style,
            composition_rules=body.composition_rules,
            realism_level=body.realism_level,
            negative_constraints=body.negative_constraints,
            reference_asset_id=body.reference_asset_id,
            is_locked=body.is_locked,
        )
    except ReferenceError as e:
        raise _map_error(e)


@router.get("/projects/{project_id}/styles", response_model=List[StyleBibleResponse])
def list_style_bibles(project_id: uuid.UUID, db: Session = Depends(get_db)):
    service = ReferenceService(db)
    try:
        return service.list_styles(project_id)
    except ReferenceError as e:
        raise _map_error(e)


@router.get("/styles/{style_id}", response_model=StyleBibleResponse)
def get_style_bible(style_id: uuid.UUID, db: Session = Depends(get_db)):
    service = ReferenceService(db)
    try:
        return service.get_style(style_id)
    except ReferenceError as e:
        raise _map_error(e)


@router.patch("/styles/{style_id}", response_model=StyleBibleResponse)
def update_style_bible(style_id: uuid.UUID, body: StyleBibleUpdate, db: Session = Depends(get_db)):
    service = ReferenceService(db)
    try:
        return service.update_style(
            style_id=style_id,
            name=body.name,
            visual_style=body.visual_style,
            camera_style=body.camera_style,
            color_direction=body.color_direction,
            lighting_style=body.lighting_style,
            composition_rules=body.composition_rules,
            realism_level=body.realism_level,
            negative_constraints=body.negative_constraints,
            reference_asset_id=body.reference_asset_id,
            is_locked=body.is_locked,
        )
    except ReferenceError as e:
        raise _map_error(e)


@router.delete("/styles/{style_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_style_bible(style_id: uuid.UUID, db: Session = Depends(get_db)):
    service = ReferenceService(db)
    try:
        service.delete_style(style_id)
    except ReferenceError as e:
        raise _map_error(e)


# --- Brand Bibles ---
@router.post("/projects/{project_id}/brands", response_model=BrandBibleResponse, status_code=status.HTTP_201_CREATED)
def create_brand_bible(project_id: uuid.UUID, body: BrandBibleCreate, db: Session = Depends(get_db)):
    service = ReferenceService(db)
    try:
        return service.create_brand(
            project_id=project_id,
            brand_name=body.brand_name,
            brand_colors=body.brand_colors,
            typography_notes=body.typography_notes,
            do_and_dont_rules=body.do_and_dont_rules,
            tone=body.tone,
            mandatory_wording=body.mandatory_wording,
            continuity_notes=body.continuity_notes,
            logo_asset_id=body.logo_asset_id,
            is_locked=body.is_locked,
        )
    except ReferenceError as e:
        raise _map_error(e)


@router.get("/projects/{project_id}/brands", response_model=List[BrandBibleResponse])
def list_brand_bibles(project_id: uuid.UUID, db: Session = Depends(get_db)):
    service = ReferenceService(db)
    try:
        return service.list_brands(project_id)
    except ReferenceError as e:
        raise _map_error(e)


@router.get("/brands/{brand_id}", response_model=BrandBibleResponse)
def get_brand_bible(brand_id: uuid.UUID, db: Session = Depends(get_db)):
    service = ReferenceService(db)
    try:
        return service.get_brand(brand_id)
    except ReferenceError as e:
        raise _map_error(e)


@router.patch("/brands/{brand_id}", response_model=BrandBibleResponse)
def update_brand_bible(brand_id: uuid.UUID, body: BrandBibleUpdate, db: Session = Depends(get_db)):
    service = ReferenceService(db)
    try:
        return service.update_brand(
            brand_id=brand_id,
            brand_name=body.brand_name,
            brand_colors=body.brand_colors,
            typography_notes=body.typography_notes,
            do_and_dont_rules=body.do_and_dont_rules,
            tone=body.tone,
            mandatory_wording=body.mandatory_wording,
            continuity_notes=body.continuity_notes,
            logo_asset_id=body.logo_asset_id,
            is_locked=body.is_locked,
        )
    except ReferenceError as e:
        raise _map_error(e)


@router.delete("/brands/{brand_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_brand_bible(brand_id: uuid.UUID, db: Session = Depends(get_db)):
    service = ReferenceService(db)
    try:
        service.delete_brand(brand_id)
    except ReferenceError as e:
        raise _map_error(e)
