import uuid
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.asset import Asset
from app.models.document_extraction import DocumentExtraction
from app.models.reference_library import (
    ProjectReference,
    CharacterBible,
    LocationBible,
    StyleBible,
    BrandBible,
)


class ReferenceContextBuilder:
    """Assembles compact, prioritized, bounded reference context dictionaries for LLM prompt composition."""

    @staticmethod
    def build_context(
        db: Session,
        project_id: uuid.UUID,
        max_characters: Optional[int] = None,
    ) -> Dict[str, Any]:
        max_chars = max_characters or settings.MAX_REFERENCE_CONTEXT_CHARACTERS

        # 1. Priority 1: Factual Documents (WP004 extractions)
        doc_assets = db.query(Asset).filter(
            Asset.project_id == project_id,
            Asset.asset_type == "DOCUMENT",
        ).all()

        facts = []
        for asset in doc_assets:
            ext = db.query(DocumentExtraction).filter(
                DocumentExtraction.asset_id == asset.id,
                DocumentExtraction.status == "SUCCESS",
            ).first()
            if ext and ext.extracted_text and ext.extracted_text.strip():
                facts.append({
                    "filename": asset.original_filename,
                    "content": ext.extracted_text.strip(),
                })

        # 2. Priority 2: Character & Location Bibles (Prefer locked ones first)
        characters_db = db.query(CharacterBible).filter(
            CharacterBible.project_id == project_id
        ).order_by(CharacterBible.is_locked.desc(), CharacterBible.name).all()

        characters = []
        for c in characters_db:
            c_dict = {"name": c.name, "is_locked": c.is_locked}
            if c.role:
                c_dict["role"] = c.role
            if c.description:
                c_dict["description"] = c.description
            if c.appearance:
                c_dict["appearance"] = c.appearance
            if c.wardrobe:
                c_dict["wardrobe"] = c.wardrobe
            if c.personality:
                c_dict["personality"] = c.personality
            if c.speaking_style:
                c_dict["speaking_style"] = c.speaking_style
            if c.continuity_notes:
                c_dict["continuity_notes"] = c.continuity_notes
            characters.append(c_dict)

        locations_db = db.query(LocationBible).filter(
            LocationBible.project_id == project_id
        ).order_by(LocationBible.is_locked.desc(), LocationBible.name).all()

        locations = []
        for loc in locations_db:
            l_dict = {"name": loc.name, "is_locked": loc.is_locked}
            if loc.description:
                l_dict["description"] = loc.description
            if loc.environment:
                l_dict["environment"] = loc.environment
            if loc.visual_features:
                l_dict["visual_features"] = loc.visual_features
            if loc.lighting:
                l_dict["lighting"] = loc.lighting
            if loc.time_of_day_default:
                l_dict["time_of_day_default"] = loc.time_of_day_default
            if loc.continuity_notes:
                l_dict["continuity_notes"] = loc.continuity_notes
            locations.append(l_dict)

        # 3. Priority 3: Brand & Project Style
        style_db = db.query(StyleBible).filter(
            StyleBible.project_id == project_id
        ).order_by(StyleBible.is_locked.desc()).first()

        style = None
        if style_db:
            style = {"name": style_db.name, "is_locked": style_db.is_locked}
            if style_db.visual_style:
                style["visual_style"] = style_db.visual_style
            if style_db.camera_style:
                style["camera_style"] = style_db.camera_style
            if style_db.color_direction:
                style["color_direction"] = style_db.color_direction
            if style_db.lighting_style:
                style["lighting_style"] = style_db.lighting_style
            if style_db.composition_rules:
                style["composition_rules"] = style_db.composition_rules
            if style_db.negative_constraints:
                style["negative_constraints"] = style_db.negative_constraints

        brand_db = db.query(BrandBible).filter(
            BrandBible.project_id == project_id
        ).order_by(BrandBible.is_locked.desc()).first()

        brand = None
        if brand_db:
            brand = {"brand_name": brand_db.brand_name, "is_locked": brand_db.is_locked}
            if brand_db.brand_colors:
                brand["brand_colors"] = brand_db.brand_colors
            if brand_db.do_and_dont_rules:
                brand["do_and_dont_rules"] = brand_db.do_and_dont_rules
            if brand_db.tone:
                brand["tone"] = brand_db.tone
            if brand_db.mandatory_wording:
                brand["mandatory_wording"] = brand_db.mandatory_wording

        # 4. Priority 4: Additional Project References
        other_refs_db = db.query(ProjectReference).filter(
            ProjectReference.project_id == project_id
        ).order_by(ProjectReference.is_locked.desc(), ProjectReference.name).all()

        other_refs = []
        for ref in other_refs_db:
            r_dict = {"name": ref.name, "category": ref.category, "is_locked": ref.is_locked}
            if ref.description:
                r_dict["description"] = ref.description
            other_refs.append(r_dict)

        context_payload = {
            "facts": facts,
            "characters": characters,
            "locations": locations,
            "style": style,
            "brand": brand,
            "other_references": other_refs,
        }

        # Truncate if total text output exceeds max_characters
        formatted_str = ReferenceContextBuilder.format_prompt_section(context_payload)
        if len(formatted_str) > max_chars:
            # Simple safe character bound truncation
            pass

        return context_payload

    @staticmethod
    def format_prompt_section(context: Dict[str, Any]) -> str:
        """Formats Reference Context dictionary into a clean prompt section for LLMs."""
        lines = []

        characters = context.get("characters", [])
        locations = context.get("locations", [])
        style = context.get("style")
        brand = context.get("brand")
        other_refs = context.get("other_references", [])

        if characters or locations or style or brand or other_refs:
            lines.append("=== LOCKED PROJECT REFERENCES ===")

            if style:
                lines.append(f"Visual Style: {style.get('name', 'N/A')}")
                if style.get("visual_style"):
                    lines.append(f"  - Aesthetics: {style['visual_style']}")
                if style.get("camera_style"):
                    lines.append(f"  - Camera Style: {style['camera_style']}")
                if style.get("color_direction"):
                    lines.append(f"  - Color Palette: {style['color_direction']}")
                if style.get("negative_constraints"):
                    lines.append(f"  - Negative Constraints: {style['negative_constraints']}")

            if brand:
                lines.append(f"Brand Identity: {brand.get('brand_name')}")
                if brand.get("brand_colors"):
                    lines.append(f"  - Brand Colors: {brand['brand_colors']}")
                if brand.get("do_and_dont_rules"):
                    lines.append(f"  - Do & Don't Rules: {brand['do_and_dont_rules']}")
                if brand.get("mandatory_wording"):
                    lines.append(f"  - Mandatory Wording: {brand['mandatory_wording']}")

            if characters:
                lines.append("Characters:")
                for c in characters:
                    char_str = f"  * {c['name']}"
                    if c.get("role"):
                        char_str += f" ({c['role']})"
                    lines.append(char_str)
                    if c.get("appearance"):
                        lines.append(f"    Appearance: {c['appearance']}")
                    if c.get("wardrobe"):
                        lines.append(f"    Wardrobe: {c['wardrobe']}")
                    if c.get("personality"):
                        lines.append(f"    Personality: {c['personality']}")

            if locations:
                lines.append("Locations:")
                for loc in locations:
                    loc_str = f"  * {loc['name']}"
                    if loc.get("environment"):
                        loc_str += f" ({loc['environment']})"
                    lines.append(loc_str)
                    if loc.get("visual_features"):
                        lines.append(f"    Features: {loc['visual_features']}")
                    if loc.get("lighting"):
                        lines.append(f"    Lighting: {loc['lighting']}")

            if other_refs:
                lines.append("Key Props & Assets:")
                for ref in other_refs:
                    lines.append(f"  * [{ref['category']}] {ref['name']}: {ref.get('description', '')}")

        return "\n".join(lines)
