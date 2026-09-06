"""Provider-neutral pricing rules and cost estimation registry."""
from typing import Optional, Dict, Any, Tuple
from pydantic import BaseModel


class CostStatus:
    ESTIMATED = "ESTIMATED"
    CONFIRMED = "CONFIRMED"
    ADJUSTED = "ADJUSTED"
    UNKNOWN = "UNKNOWN"


class ProviderPricingRule(BaseModel):
    provider: str
    operation: str
    model: Optional[str] = None
    cost_per_second: Optional[float] = None
    cost_per_generation: Optional[float] = None
    cost_per_1k_prompt_tokens: Optional[float] = None
    cost_per_1k_completion_tokens: Optional[float] = None
    currency: str = "USD"


class ProviderPricingService:
    """Provider-neutral pricing registry and cost estimation service."""

    _registry: Dict[Tuple[str, str, Optional[str]], ProviderPricingRule] = {}
    _default_rules: Dict[Tuple[str, str], ProviderPricingRule] = {}

    @classmethod
    def reset(cls):
        """Reset registry to default state (useful for tests)."""
        cls._registry.clear()
        cls._default_rules.clear()
        cls._init_defaults()

    @classmethod
    def register_rule(cls, rule: ProviderPricingRule):
        key = (
            rule.provider.lower(),
            rule.operation.upper(),
            rule.model.lower() if rule.model else None,
        )
        cls._registry[key] = rule
        fallback_key = (rule.provider.lower(), rule.operation.upper())
        if fallback_key not in cls._default_rules or rule.model is None:
            cls._default_rules[fallback_key] = rule

    @classmethod
    def get_rule(
        cls, provider: str, operation: str, model: Optional[str] = None
    ) -> Optional[ProviderPricingRule]:
        provider_clean = provider.lower()
        op_clean = operation.upper()
        model_clean = model.lower() if model else None

        if model_clean:
            rule = cls._registry.get((provider_clean, op_clean, model_clean))
            if rule:
                return rule

        rule = cls._registry.get((provider_clean, op_clean, None))
        if rule:
            return rule

        return cls._default_rules.get((provider_clean, op_clean))

    @classmethod
    def estimate_cost(
        cls,
        provider: str,
        operation: str,
        model: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Optional[float], str, str]:
        """Returns (estimated_cost, currency, cost_status).

        If pricing cannot be determined, cost_status is UNKNOWN and estimated_cost is None.
        """
        rule = cls.get_rule(provider, operation, model)
        if not rule:
            return None, "USD", CostStatus.UNKNOWN

        params = params or {}
        estimated = 0.0
        has_pricing = False

        if rule.cost_per_second is not None:
            duration = float(params.get("duration_seconds") or 4.0)
            estimated += duration * rule.cost_per_second
            has_pricing = True

        if rule.cost_per_generation is not None:
            estimated += rule.cost_per_generation
            has_pricing = True

        if rule.cost_per_1k_prompt_tokens is not None and "prompt_tokens" in params:
            tokens = float(params["prompt_tokens"])
            estimated += (tokens / 1000.0) * rule.cost_per_1k_prompt_tokens
            has_pricing = True

        if rule.cost_per_1k_completion_tokens is not None and "completion_tokens" in params:
            tokens = float(params["completion_tokens"])
            estimated += (tokens / 1000.0) * rule.cost_per_1k_completion_tokens
            has_pricing = True

        if not has_pricing:
            return None, rule.currency, CostStatus.UNKNOWN

        return round(estimated, 4), rule.currency, CostStatus.ESTIMATED

    @classmethod
    def _init_defaults(cls):
        cls.register_rule(
            ProviderPricingRule(
                provider="vidu",
                operation="VIDEO_GENERATION",
                cost_per_second=0.05,
                currency="USD",
            )
        )
        cls.register_rule(
            ProviderPricingRule(
                provider="vidu",
                operation="TEXT_TO_VIDEO",
                cost_per_second=0.05,
                currency="USD",
            )
        )
        cls.register_rule(
            ProviderPricingRule(
                provider="vidu",
                operation="REFERENCE_TO_VIDEO",
                cost_per_second=0.05,
                currency="USD",
            )
        )
        cls.register_rule(
            ProviderPricingRule(
                provider="openai",
                operation="STORY_GENERATION",
                model="gpt-4o",
                cost_per_1k_prompt_tokens=0.005,
                cost_per_1k_completion_tokens=0.015,
                currency="USD",
            )
        )


ProviderPricingService._init_defaults()
