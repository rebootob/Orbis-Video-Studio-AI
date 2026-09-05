import uuid
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.models.project import Project
from app.models.asset import Asset
from app.models.reference_library import (
    ProjectReference,
    CharacterBible,
    LocationBible,
    StyleBible,
    BrandBible,
)


class ReferenceError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class ReferenceService:
    """Core domain service for Reference Library and Continuity Bibles CRUD and safety enforcement."""

    def __init__(self, db: Session):
        self.db = db

    def _verify_project_exists(self, project_id: uuid.UUID) -> Project:
        project = self.db.get(Project, project_id)
        if not project:
            raise ReferenceError("PROJECT_NOT_FOUND", f"Project with ID '{project_id}' not found.")
        return project

    def _validate_asset_link(self, project_id: uuid.UUID, asset_id: Optional[uuid.UUID]) -> None:
        if not asset_id:
            return
        asset = self.db.get(Asset, asset_id)
        if not asset:
            raise ReferenceError("INVALID_ASSET_LINK", f"Referenced asset with ID '{asset_id}' not found.")
        if asset.project_id != project_id:
            raise ReferenceError(
                "INVALID_ASSET_LINK",
                f"Referenced asset '{asset_id}' belongs to project '{asset.project_id}', not project '{project_id}'. Cross-project asset linking is prohibited.",
            )

    # --- Project Reference CRUD ---
    def create_reference(
        self,
        project_id: uuid.UUID,
        name: str,
        category: str,
        description: Optional[str] = None,
        reference_asset_id: Optional[uuid.UUID] = None,
        is_locked: bool = False,
        metadata_json: Optional[Dict[str, Any]] = None,
    ) -> ProjectReference:
        self._verify_project_exists(project_id)
        self._validate_asset_link(project_id, reference_asset_id)

        valid_categories = {
            "CHARACTER", "LOCATION", "STYLE", "BRAND", "PROP",
            "DOCUMENT", "IMAGE", "VIDEO", "AUDIO", "OTHER",
        }
        cat_upper = category.upper()
        if cat_upper not in valid_categories:
            raise ReferenceError("INVALID_CATEGORY", f"Invalid reference category '{category}'. Valid: {sorted(valid_categories)}")

        ref = ProjectReference(
            id=uuid.uuid4(),
            project_id=project_id,
            name=name,
            category=cat_upper,
            description=description,
            reference_asset_id=reference_asset_id,
            is_locked=is_locked,
            metadata_json=metadata_json,
        )
        self.db.add(ref)
        self.db.commit()
        self.db.refresh(ref)
        return ref

    def list_references(self, project_id: uuid.UUID, category: Optional[str] = None) -> List[ProjectReference]:
        self._verify_project_exists(project_id)
        query = self.db.query(ProjectReference).filter(ProjectReference.project_id == project_id)
        if category:
            query = query.filter(ProjectReference.category == category.upper())
        return query.order_by(ProjectReference.name).all()

    def get_reference(self, reference_id: uuid.UUID) -> ProjectReference:
        ref = self.db.get(ProjectReference, reference_id)
        if not ref:
            raise ReferenceError("REFERENCE_NOT_FOUND", f"ProjectReference with ID '{reference_id}' not found.")
        return ref

    def update_reference(
        self,
        reference_id: uuid.UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        reference_asset_id: Optional[uuid.UUID] = None,
        is_locked: Optional[bool] = None,
        metadata_json: Optional[Dict[str, Any]] = None,
    ) -> ProjectReference:
        ref = self.get_reference(reference_id)

        # Check lock safety: if locked and update is not unlocking it
        if ref.is_locked and (is_locked is None or is_locked is True):
            raise ReferenceError("REFERENCE_LOCKED", f"ProjectReference '{reference_id}' is locked. Explicit unlock required before modification.")

        if reference_asset_id is not None:
            self._validate_asset_link(ref.project_id, reference_asset_id)
            ref.reference_asset_id = reference_asset_id

        if name is not None:
            ref.name = name
        if description is not None:
            ref.description = description
        if is_locked is not None:
            ref.is_locked = is_locked
        if metadata_json is not None:
            ref.metadata_json = metadata_json

        self.db.commit()
        self.db.refresh(ref)
        return ref

    def delete_reference(self, reference_id: uuid.UUID) -> None:
        ref = self.get_reference(reference_id)
        if ref.is_locked:
            raise ReferenceError("REFERENCE_LOCKED", f"ProjectReference '{reference_id}' is locked and cannot be deleted.")
        self.db.delete(ref)
        self.db.commit()

    # --- Character Bible CRUD ---
    def create_character(
        self,
        project_id: uuid.UUID,
        name: str,
        role: Optional[str] = None,
        description: Optional[str] = None,
        appearance: Optional[str] = None,
        wardrobe: Optional[str] = None,
        age_range: Optional[str] = None,
        gender_presentation: Optional[str] = None,
        nationality_cultural_context: Optional[str] = None,
        personality: Optional[str] = None,
        speaking_style: Optional[str] = None,
        continuity_notes: Optional[str] = None,
        reference_asset_id: Optional[uuid.UUID] = None,
        is_locked: bool = False,
    ) -> CharacterBible:
        self._verify_project_exists(project_id)
        self._validate_asset_link(project_id, reference_asset_id)

        char = CharacterBible(
            id=uuid.uuid4(),
            project_id=project_id,
            name=name,
            role=role,
            description=description,
            appearance=appearance,
            wardrobe=wardrobe,
            age_range=age_range,
            gender_presentation=gender_presentation,
            nationality_cultural_context=nationality_cultural_context,
            personality=personality,
            speaking_style=speaking_style,
            continuity_notes=continuity_notes,
            reference_asset_id=reference_asset_id,
            is_locked=is_locked,
        )
        self.db.add(char)
        self.db.commit()
        self.db.refresh(char)
        return char

    def list_characters(self, project_id: uuid.UUID) -> List[CharacterBible]:
        self._verify_project_exists(project_id)
        return self.db.query(CharacterBible).filter(CharacterBible.project_id == project_id).order_by(CharacterBible.name).all()

    def get_character(self, character_id: uuid.UUID) -> CharacterBible:
        char = self.db.get(CharacterBible, character_id)
        if not char:
            raise ReferenceError("CHARACTER_NOT_FOUND", f"CharacterBible with ID '{character_id}' not found.")
        return char

    def update_character(
        self,
        character_id: uuid.UUID,
        name: Optional[str] = None,
        role: Optional[str] = None,
        description: Optional[str] = None,
        appearance: Optional[str] = None,
        wardrobe: Optional[str] = None,
        age_range: Optional[str] = None,
        gender_presentation: Optional[str] = None,
        nationality_cultural_context: Optional[str] = None,
        personality: Optional[str] = None,
        speaking_style: Optional[str] = None,
        continuity_notes: Optional[str] = None,
        reference_asset_id: Optional[uuid.UUID] = None,
        is_locked: Optional[bool] = None,
    ) -> CharacterBible:
        char = self.get_character(character_id)
        if char.is_locked and (is_locked is None or is_locked is True):
            raise ReferenceError("REFERENCE_LOCKED", f"CharacterBible '{character_id}' is locked. Explicit unlock required.")

        if reference_asset_id is not None:
            self._validate_asset_link(char.project_id, reference_asset_id)
            char.reference_asset_id = reference_asset_id

        if name is not None:
            char.name = name
        if role is not None:
            char.role = role
        if description is not None:
            char.description = description
        if appearance is not None:
            char.appearance = appearance
        if wardrobe is not None:
            char.wardrobe = wardrobe
        if age_range is not None:
            char.age_range = age_range
        if gender_presentation is not None:
            char.gender_presentation = gender_presentation
        if nationality_cultural_context is not None:
            char.nationality_cultural_context = nationality_cultural_context
        if personality is not None:
            char.personality = personality
        if speaking_style is not None:
            char.speaking_style = speaking_style
        if continuity_notes is not None:
            char.continuity_notes = continuity_notes
        if is_locked is not None:
            char.is_locked = is_locked

        self.db.commit()
        self.db.refresh(char)
        return char

    def delete_character(self, character_id: uuid.UUID) -> None:
        char = self.get_character(character_id)
        if char.is_locked:
            raise ReferenceError("REFERENCE_LOCKED", f"CharacterBible '{character_id}' is locked and cannot be deleted.")
        self.db.delete(char)
        self.db.commit()

    # --- Location Bible CRUD ---
    def create_location(
        self,
        project_id: uuid.UUID,
        name: str,
        description: Optional[str] = None,
        environment: Optional[str] = None,
        visual_features: Optional[str] = None,
        lighting: Optional[str] = None,
        time_of_day_default: Optional[str] = None,
        continuity_notes: Optional[str] = None,
        reference_asset_id: Optional[uuid.UUID] = None,
        is_locked: bool = False,
    ) -> LocationBible:
        self._verify_project_exists(project_id)
        self._validate_asset_link(project_id, reference_asset_id)

        loc = LocationBible(
            id=uuid.uuid4(),
            project_id=project_id,
            name=name,
            description=description,
            environment=environment,
            visual_features=visual_features,
            lighting=lighting,
            time_of_day_default=time_of_day_default,
            continuity_notes=continuity_notes,
            reference_asset_id=reference_asset_id,
            is_locked=is_locked,
        )
        self.db.add(loc)
        self.db.commit()
        self.db.refresh(loc)
        return loc

    def list_locations(self, project_id: uuid.UUID) -> List[LocationBible]:
        self._verify_project_exists(project_id)
        return self.db.query(LocationBible).filter(LocationBible.project_id == project_id).order_by(LocationBible.name).all()

    def get_location(self, location_id: uuid.UUID) -> LocationBible:
        loc = self.db.get(LocationBible, location_id)
        if not loc:
            raise ReferenceError("LOCATION_NOT_FOUND", f"LocationBible with ID '{location_id}' not found.")
        return loc

    def update_location(
        self,
        location_id: uuid.UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        environment: Optional[str] = None,
        visual_features: Optional[str] = None,
        lighting: Optional[str] = None,
        time_of_day_default: Optional[str] = None,
        continuity_notes: Optional[str] = None,
        reference_asset_id: Optional[uuid.UUID] = None,
        is_locked: Optional[bool] = None,
    ) -> LocationBible:
        loc = self.get_location(location_id)
        if loc.is_locked and (is_locked is None or is_locked is True):
            raise ReferenceError("REFERENCE_LOCKED", f"LocationBible '{location_id}' is locked. Explicit unlock required.")

        if reference_asset_id is not None:
            self._validate_asset_link(loc.project_id, reference_asset_id)
            loc.reference_asset_id = reference_asset_id

        if name is not None:
            loc.name = name
        if description is not None:
            loc.description = description
        if environment is not None:
            loc.environment = environment
        if visual_features is not None:
            loc.visual_features = visual_features
        if lighting is not None:
            loc.lighting = lighting
        if time_of_day_default is not None:
            loc.time_of_day_default = time_of_day_default
        if continuity_notes is not None:
            loc.continuity_notes = continuity_notes
        if is_locked is not None:
            loc.is_locked = is_locked

        self.db.commit()
        self.db.refresh(loc)
        return loc

    def delete_location(self, location_id: uuid.UUID) -> None:
        loc = self.get_location(location_id)
        if loc.is_locked:
            raise ReferenceError("REFERENCE_LOCKED", f"LocationBible '{location_id}' is locked and cannot be deleted.")
        self.db.delete(loc)
        self.db.commit()

    # --- Style Bible CRUD ---
    def create_style(
        self,
        project_id: uuid.UUID,
        name: str,
        visual_style: Optional[str] = None,
        camera_style: Optional[str] = None,
        color_direction: Optional[str] = None,
        lighting_style: Optional[str] = None,
        composition_rules: Optional[str] = None,
        realism_level: Optional[str] = None,
        negative_constraints: Optional[str] = None,
        reference_asset_id: Optional[uuid.UUID] = None,
        is_locked: bool = False,
    ) -> StyleBible:
        self._verify_project_exists(project_id)
        self._validate_asset_link(project_id, reference_asset_id)

        style = StyleBible(
            id=uuid.uuid4(),
            project_id=project_id,
            name=name,
            visual_style=visual_style,
            camera_style=camera_style,
            color_direction=color_direction,
            lighting_style=lighting_style,
            composition_rules=composition_rules,
            realism_level=realism_level,
            negative_constraints=negative_constraints,
            reference_asset_id=reference_asset_id,
            is_locked=is_locked,
        )
        self.db.add(style)
        self.db.commit()
        self.db.refresh(style)
        return style

    def list_styles(self, project_id: uuid.UUID) -> List[StyleBible]:
        self._verify_project_exists(project_id)
        return self.db.query(StyleBible).filter(StyleBible.project_id == project_id).order_by(StyleBible.name).all()

    def get_style(self, style_id: uuid.UUID) -> StyleBible:
        style = self.db.get(StyleBible, style_id)
        if not style:
            raise ReferenceError("STYLE_NOT_FOUND", f"StyleBible with ID '{style_id}' not found.")
        return style

    def update_style(
        self,
        style_id: uuid.UUID,
        name: Optional[str] = None,
        visual_style: Optional[str] = None,
        camera_style: Optional[str] = None,
        color_direction: Optional[str] = None,
        lighting_style: Optional[str] = None,
        composition_rules: Optional[str] = None,
        realism_level: Optional[str] = None,
        negative_constraints: Optional[str] = None,
        reference_asset_id: Optional[uuid.UUID] = None,
        is_locked: Optional[bool] = None,
    ) -> StyleBible:
        style = self.get_style(style_id)
        if style.is_locked and (is_locked is None or is_locked is True):
            raise ReferenceError("REFERENCE_LOCKED", f"StyleBible '{style_id}' is locked. Explicit unlock required.")

        if reference_asset_id is not None:
            self._validate_asset_link(style.project_id, reference_asset_id)
            style.reference_asset_id = reference_asset_id

        if name is not None:
            style.name = name
        if visual_style is not None:
            style.visual_style = visual_style
        if camera_style is not None:
            style.camera_style = camera_style
        if color_direction is not None:
            style.color_direction = color_direction
        if lighting_style is not None:
            style.lighting_style = lighting_style
        if composition_rules is not None:
            style.composition_rules = composition_rules
        if realism_level is not None:
            style.realism_level = realism_level
        if negative_constraints is not None:
            style.negative_constraints = negative_constraints
        if is_locked is not None:
            style.is_locked = is_locked

        self.db.commit()
        self.db.refresh(style)
        return style

    def delete_style(self, style_id: uuid.UUID) -> None:
        style = self.get_style(style_id)
        if style.is_locked:
            raise ReferenceError("REFERENCE_LOCKED", f"StyleBible '{style_id}' is locked and cannot be deleted.")
        self.db.delete(style)
        self.db.commit()

    # --- Brand Bible CRUD ---
    def create_brand(
        self,
        project_id: uuid.UUID,
        brand_name: str,
        brand_colors: Optional[str] = None,
        typography_notes: Optional[str] = None,
        do_and_dont_rules: Optional[str] = None,
        tone: Optional[str] = None,
        mandatory_wording: Optional[str] = None,
        continuity_notes: Optional[str] = None,
        logo_asset_id: Optional[uuid.UUID] = None,
        is_locked: bool = False,
    ) -> BrandBible:
        self._verify_project_exists(project_id)
        self._validate_asset_link(project_id, logo_asset_id)

        brand = BrandBible(
            id=uuid.uuid4(),
            project_id=project_id,
            brand_name=brand_name,
            brand_colors=brand_colors,
            typography_notes=typography_notes,
            do_and_dont_rules=do_and_dont_rules,
            tone=tone,
            mandatory_wording=mandatory_wording,
            continuity_notes=continuity_notes,
            logo_asset_id=logo_asset_id,
            is_locked=is_locked,
        )
        self.db.add(brand)
        self.db.commit()
        self.db.refresh(brand)
        return brand

    def list_brands(self, project_id: uuid.UUID) -> List[BrandBible]:
        self._verify_project_exists(project_id)
        return self.db.query(BrandBible).filter(BrandBible.project_id == project_id).order_by(BrandBible.brand_name).all()

    def get_brand(self, brand_id: uuid.UUID) -> BrandBible:
        brand = self.db.get(BrandBible, brand_id)
        if not brand:
            raise ReferenceError("BRAND_NOT_FOUND", f"BrandBible with ID '{brand_id}' not found.")
        return brand

    def update_brand(
        self,
        brand_id: uuid.UUID,
        brand_name: Optional[str] = None,
        brand_colors: Optional[str] = None,
        typography_notes: Optional[str] = None,
        do_and_dont_rules: Optional[str] = None,
        tone: Optional[str] = None,
        mandatory_wording: Optional[str] = None,
        continuity_notes: Optional[str] = None,
        logo_asset_id: Optional[uuid.UUID] = None,
        is_locked: Optional[bool] = None,
    ) -> BrandBible:
        brand = self.get_brand(brand_id)
        if brand.is_locked and (is_locked is None or is_locked is True):
            raise ReferenceError("REFERENCE_LOCKED", f"BrandBible '{brand_id}' is locked. Explicit unlock required.")

        if logo_asset_id is not None:
            self._validate_asset_link(brand.project_id, logo_asset_id)
            brand.logo_asset_id = logo_asset_id

        if brand_name is not None:
            brand.brand_name = brand_name
        if brand_colors is not None:
            brand.brand_colors = brand_colors
        if typography_notes is not None:
            brand.typography_notes = typography_notes
        if do_and_dont_rules is not None:
            brand.do_and_dont_rules = do_and_dont_rules
        if tone is not None:
            brand.tone = tone
        if mandatory_wording is not None:
            brand.mandatory_wording = mandatory_wording
        if continuity_notes is not None:
            brand.continuity_notes = continuity_notes
        if is_locked is not None:
            brand.is_locked = is_locked

        self.db.commit()
        self.db.refresh(brand)
        return brand

    def delete_brand(self, brand_id: uuid.UUID) -> None:
        brand = self.get_brand(brand_id)
        if brand.is_locked:
            raise ReferenceError("REFERENCE_LOCKED", f"BrandBible '{brand_id}' is locked and cannot be deleted.")
        self.db.delete(brand)
        self.db.commit()
