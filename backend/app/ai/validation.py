# Dialogue Validation System for AI-Powered Tuxemon
# Austin Kidwell | Intellegix | Mobile-First Pokemon-Style Game

import json
import re
from typing import Dict, List, Optional, Tuple, Set
from enum import Enum
from dataclasses import dataclass

from loguru import logger
from pydantic import BaseModel

from app.game.models import DialogueResponse, NPCInteractionContext


class ValidationSeverity(str, Enum):
    """Severity levels for validation issues."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationResult:
    """Result of dialogue validation."""
    is_valid: bool
    severity: ValidationSeverity
    issues: List[str]
    score: float  # 0.0 = invalid, 1.0 = perfect
    suggested_fixes: List[str]


class CanonFact(BaseModel):
    """A single canon fact about the game world."""
    id: str
    category: str  # "lore", "mechanics", "characters", "locations"
    fact: str
    keywords: List[str]
    importance: float = 1.0  # 0.0-1.0, higher = more important to preserve


class DialogueValidator:
    """Validates AI-generated dialogue against game canon and constraints."""

    def __init__(self):
        self.canon_facts: Dict[str, CanonFact] = {}
        self.forbidden_topics: Set[str] = set()
        self.required_tone_keywords: Dict[str, List[str]] = {}
        self.initialize_canon_database()

    def initialize_canon_database(self):
        """Initialize the canon facts database."""
        # Core Tuxemon lore and mechanics
        canon_data = [
            {
                "id": "world_setting",
                "category": "lore",
                "fact": "Tuxemon takes place in a world where monsters can be tamed and trained by humans",
                "keywords": ["world", "setting", "monsters", "tamed", "trained", "humans"],
                "importance": 1.0,
            },
            {
                "id": "monster_mechanics",
                "category": "mechanics",
                "fact": "Monsters have elements, stats, and can learn techniques in battle",
                "keywords": ["monsters", "elements", "stats", "techniques", "battle", "combat"],
                "importance": 0.9,
            },
            {
                "id": "capture_system",
                "category": "mechanics",
                "fact": "Wild monsters can be captured using capture devices and items",
                "keywords": ["capture", "wild", "monsters", "devices", "items", "catch"],
                "importance": 0.8,
            },
            {
                "id": "trainer_culture",
                "category": "lore",
                "fact": "People who train monsters are called trainers and often travel to improve their skills",
                "keywords": ["trainers", "travel", "improve", "skills", "training", "journey"],
                "importance": 0.7,
            },
            {
                "id": "no_violence_humans",
                "category": "constraints",
                "fact": "Tuxemon is family-friendly: no violence between humans, no death, no inappropriate content",
                "keywords": ["violence", "death", "inappropriate", "family-friendly", "safe"],
                "importance": 1.0,
            },
            {
                "id": "healing_centers",
                "category": "lore",
                "fact": "Towns have healing centers where trainers can restore their monsters' health",
                "keywords": ["healing", "centers", "towns", "restore", "health", "monsters"],
                "importance": 0.6,
            },
            {
                "id": "starting_town",
                "category": "locations",
                "fact": "Players begin their journey in a peaceful starting town with friendly NPCs",
                "keywords": ["starting", "town", "peaceful", "friendly", "begin", "journey"],
                "importance": 0.8,
            },
        ]

        # Additional AI-specific constraints
        ai_constraints = [
            {
                "id": "no_meta_references",
                "category": "constraints",
                "fact": "NPCs should never reference being AI, being in a game, or break the fourth wall",
                "keywords": ["AI", "game", "player", "character", "fourth wall", "meta"],
                "importance": 1.0,
            },
            {
                "id": "consistent_personality",
                "category": "constraints",
                "fact": "NPCs must maintain consistent personality traits and behavior patterns",
                "keywords": ["personality", "consistent", "behavior", "traits", "character"],
                "importance": 0.9,
            },
            {
                "id": "appropriate_knowledge",
                "category": "constraints",
                "fact": "NPCs should only know information their character would realistically know",
                "keywords": ["knowledge", "realistic", "character", "information", "know"],
                "importance": 0.8,
            },
        ]

        # Load all facts into the database
        all_facts = canon_data + ai_constraints
        for fact_data in all_facts:
            fact = CanonFact(**fact_data)
            self.canon_facts[fact.id] = fact

        # Initialize forbidden topics
        self.forbidden_topics = {
            "real_world_references", "modern_technology", "politics", "religion",
            "violence_between_humans", "death", "inappropriate_content",
            "fourth_wall_breaking", "meta_gaming_concepts"
        }

        logger.info(f"Initialized canon database with {len(self.canon_facts)} facts")

    def validate_dialogue(
        self,
        dialogue: DialogueResponse,
        context: NPCInteractionContext,
        npc_personality_traits: Optional[Dict[str, float]] = None,
    ) -> ValidationResult:
        """Validate AI-generated dialogue against canon and constraints."""
        issues = []
        score = 1.0
        severity = ValidationSeverity.INFO

        # Check for canon violations
        canon_issues, canon_score = self._check_canon_violations(dialogue.text)
        issues.extend(canon_issues)
        score *= canon_score

        # Check for forbidden content
        content_issues, content_score = self._check_forbidden_content(dialogue.text)
        issues.extend(content_issues)
        score *= content_score

        # Check tone and personality consistency
        tone_issues, tone_score = self._check_tone_consistency(
            dialogue, context, npc_personality_traits
        )
        issues.extend(tone_issues)
        score *= tone_score

        # Check for meta-references and fourth wall breaks
        meta_issues, meta_score = self._check_meta_references(dialogue.text)
        issues.extend(meta_issues)
        score *= meta_score

        # Check dialogue length and mobile-friendliness
        length_issues, length_score = self._check_mobile_constraints(dialogue.text)
        issues.extend(length_issues)
        score *= length_score

        # Determine overall severity
        if score < 0.5:
            severity = ValidationSeverity.CRITICAL
        elif score < 0.7:
            severity = ValidationSeverity.ERROR
        elif score < 0.9:
            severity = ValidationSeverity.WARNING

        is_valid = score >= 0.7 and severity != ValidationSeverity.CRITICAL

        suggested_fixes = self._generate_suggestions(issues, dialogue, context)

        return ValidationResult(
            is_valid=is_valid,
            severity=severity,
            issues=issues,
            score=score,
            suggested_fixes=suggested_fixes,
        )

    def _check_canon_violations(self, text: str) -> Tuple[List[str], float]:
        """Check for violations of established canon facts."""
        issues = []
        score = 1.0
        text_lower = text.lower()

        # Check each canon fact for potential violations
        for fact_id, fact in self.canon_facts.items():
            if fact.category == "constraints":
                continue  # Handle constraints separately

            # Look for keywords that might indicate this topic is being discussed
            relevant_keywords = [kw for kw in fact.keywords if kw in text_lower]

            if relevant_keywords:
                # This dialogue touches on this canon topic
                # For now, we'll be permissive and only flag obvious contradictions
                # More sophisticated semantic analysis could be added here

                contradiction_patterns = [
                    f"monsters (can't|cannot|don't|do not) (be|get) (captured|caught|tamed)",
                    f"(no|there are no) (healing|health) (centers|stations)",
                    f"monsters (are not|aren't) real",
                    f"(trainers|people) (can't|cannot) (train|tame) monsters",
                ]

                for pattern in contradiction_patterns:
                    if re.search(pattern, text_lower):
                        issues.append(f"Potential canon contradiction: {fact.fact}")
                        score *= 0.7  # Reduce score for canon issues
                        break

        return issues, score

    def _check_forbidden_content(self, text: str) -> Tuple[List[str], float]:
        """Check for forbidden topics and inappropriate content."""
        issues = []
        score = 1.0
        text_lower = text.lower()

        # Forbidden content patterns
        forbidden_patterns = {
            "violence": [
                r"\b(kill|murder|death|die|dead|blood)\b",
                r"\b(hurt|harm|pain|suffer)\b.*\b(human|person|people)\b",
            ],
            "inappropriate": [
                r"\b(sex|sexual|adult|mature)\b",
                r"\b(drug|alcohol|drunk|high)\b",
                r"\b(hate|racism|discrimination)\b",
            ],
            "real_world": [
                r"\b(internet|wifi|smartphone|computer|laptop)\b",
                r"\b(facebook|twitter|instagram|youtube)\b",
                r"\b(covid|pandemic|politics|election)\b",
            ],
            "meta_gaming": [
                r"\b(NPC|player character|game|level|stats|HP|MP)\b",
                r"\b(developer|programmer|code|bug|glitch)\b",
                r"\b(save|load|reset|restart)\b",
            ],
        }

        for category, patterns in forbidden_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    issues.append(f"Contains forbidden {category} content")
                    score *= 0.5  # Severe penalty for forbidden content
                    break

        return issues, score

    def _check_tone_consistency(
        self,
        dialogue: DialogueResponse,
        context: NPCInteractionContext,
        personality_traits: Optional[Dict[str, float]],
    ) -> Tuple[List[str], float]:
        """Check if dialogue tone matches NPC personality and relationship level."""
        issues = []
        score = 1.0
        text_lower = dialogue.text.lower()

        # Check relationship-appropriate tone
        relationship_level = context.relationship_level

        if relationship_level < 0.2:  # Strangers
            friendly_patterns = [r"\b(buddy|friend|pal|dear|honey)\b"]
            for pattern in friendly_patterns:
                if re.search(pattern, text_lower):
                    issues.append("Too familiar tone for low relationship level")
                    score *= 0.9

        elif relationship_level > 0.8:  # Close friends
            formal_patterns = [r"\b(sir|madam|stranger|unknown)\b"]
            for pattern in formal_patterns:
                if re.search(pattern, text_lower):
                    issues.append("Too formal tone for high relationship level")
                    score *= 0.9

        # Check personality consistency (if traits provided)
        if personality_traits:
            verbosity = personality_traits.get("verbosity", 0.5)
            friendliness = personality_traits.get("friendliness", 0.5)

            # Check verbosity consistency
            word_count = len(dialogue.text.split())
            if verbosity < 0.3 and word_count > 50:
                issues.append("Too verbose for quiet personality")
                score *= 0.9
            elif verbosity > 0.7 and word_count < 10:
                issues.append("Too brief for talkative personality")
                score *= 0.9

            # Check friendliness consistency
            if friendliness < 0.3 and dialogue.emotion in ["happy", "excited"]:
                issues.append("Too positive emotion for reserved personality")
                score *= 0.9
            elif friendliness > 0.7 and dialogue.emotion in ["angry", "sad"]:
                issues.append("Negative emotion unusual for friendly personality")
                score *= 0.95

        return issues, score

    def _check_meta_references(self, text: str) -> Tuple[List[str], float]:
        """Check for fourth wall breaks and meta-gaming references."""
        issues = []
        score = 1.0
        text_lower = text.lower()

        meta_patterns = [
            r"\b(I am an? (AI|bot|NPC|character))\b",
            r"\b(this is a (game|simulation|program))\b",
            r"\b(you are (a )?player)\b",
            r"\b(press (a )?button|click|keyboard|mouse)\b",
            r"\b(loading|saving|menu|interface)\b",
            r"\b(developer|programmer|coder)\b",
            r"\b(fourth wall|meta)\b",
        ]

        for pattern in meta_patterns:
            if re.search(pattern, text_lower):
                issues.append("Contains meta-gaming or fourth wall breaking references")
                score *= 0.3  # Severe penalty for breaking immersion
                break

        return issues, score

    def _check_mobile_constraints(self, text: str) -> Tuple[List[str], float]:
        """Check if dialogue meets mobile display requirements."""
        issues = []
        score = 1.0

        # Check length
        word_count = len(text.split())
        if word_count > 100:
            issues.append(f"Dialogue too long for mobile ({word_count} words, max 100)")
            score *= 0.8

        # Check for very long sentences
        sentences = text.split(".")
        for sentence in sentences:
            if len(sentence.strip()) > 200:  # characters
                issues.append("Contains very long sentences that may be hard to read on mobile")
                score *= 0.9
                break

        # Check for special characters that might not display well
        problematic_chars = ["€", "£", "¥", "©", "®", "™", "§"]
        if any(char in text for char in problematic_chars):
            issues.append("Contains special characters that may not display properly")
            score *= 0.95

        return issues, score

    def _generate_suggestions(
        self,
        issues: List[str],
        dialogue: DialogueResponse,
        context: NPCInteractionContext,
    ) -> List[str]:
        """Generate suggestions for fixing validation issues."""
        suggestions = []

        for issue in issues:
            if "too long" in issue.lower():
                suggestions.append("Shorten the dialogue to under 100 words")
            elif "forbidden" in issue.lower():
                suggestions.append("Remove inappropriate content and keep dialogue family-friendly")
            elif "meta" in issue.lower() or "fourth wall" in issue.lower():
                suggestions.append("Stay in character and avoid breaking immersion")
            elif "tone" in issue.lower():
                suggestions.append("Adjust tone to match NPC personality and relationship level")
            elif "canon" in issue.lower():
                suggestions.append("Ensure dialogue aligns with established game lore and mechanics")

        # Add general suggestions
        if not suggestions:
            suggestions.append("Minor improvements could enhance dialogue quality")

        return suggestions

    def get_canon_summary(self) -> Dict[str, List[str]]:
        """Get a summary of canon facts by category for reference."""
        summary = {}
        for fact in self.canon_facts.values():
            if fact.category not in summary:
                summary[fact.category] = []
            summary[fact.category].append(fact.fact)
        return summary

    def add_custom_fact(self, fact: CanonFact):
        """Add a custom canon fact to the database."""
        self.canon_facts[fact.id] = fact
        logger.info(f"Added custom canon fact: {fact.id}")

    def get_validation_stats(self) -> Dict[str, int]:
        """Get statistics about the validation system."""
        return {
            "total_canon_facts": len(self.canon_facts),
            "forbidden_topics": len(self.forbidden_topics),
            "constraint_facts": len([f for f in self.canon_facts.values() if f.category == "constraints"]),
            "lore_facts": len([f for f in self.canon_facts.values() if f.category == "lore"]),
        }


# Global dialogue validator instance
dialogue_validator = DialogueValidator()