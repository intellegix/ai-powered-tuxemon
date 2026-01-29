# Local LLM Integration for AI-Powered Tuxemon
# Austin Kidwell | Intellegix | Mobile-First Pokemon-Style Game

import asyncio
import json
import httpx
import time
from typing import Dict, List, Optional, Any
from datetime import datetime

from loguru import logger
from pydantic import BaseModel

from app.config import get_settings
from app.game.models import (
    DialogueResponse,
    PersonalityTraits,
    NPCInteractionContext,
    MemoryItem,
)

settings = get_settings()


class LocalLLMConfig(BaseModel):
    """Configuration for local LLM integration."""
    ollama_base_url: str
    model_name: str
    timeout_seconds: int = 10
    max_tokens: int = 200
    temperature: float = 0.7
    enabled: bool


class LocalLLMManager:
    """Manages local LLM integration using Ollama."""

    def __init__(self):
        self.config = LocalLLMConfig(
            ollama_base_url=settings.ollama_base_url,
            model_name=settings.local_llm_model,
            enabled=settings.local_llm_enabled,
        )
        self.client: Optional[httpx.AsyncClient] = None
        self.model_loaded = False
        self.last_health_check = datetime.min
        self.health_check_interval = 300  # 5 minutes

    async def initialize(self):
        """Initialize the local LLM client."""
        try:
            self.client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.timeout_seconds),
                limits=httpx.Limits(max_connections=5, max_keepalive_connections=2)
            )

            # Check if Ollama is available and model is loaded
            await self._health_check()

            if self.model_loaded:
                logger.info(f"✅ Local LLM initialized with model {self.config.model_name}")
            else:
                logger.warning("⚠️ Local LLM available but model not loaded")

        except Exception as e:
            logger.warning(f"❌ Failed to initialize local LLM: {e}")
            self.config.enabled = False

    async def _health_check(self) -> bool:
        """Check if Ollama is running and model is available."""
        try:
            if not self.client:
                return False

            current_time = datetime.utcnow()
            if (current_time - self.last_health_check).total_seconds() < self.health_check_interval:
                return self.model_loaded

            # Check if Ollama is running
            response = await self.client.get(f"{self.config.ollama_base_url}/api/tags")

            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [model.get("name", "") for model in models]

                # Check if our target model is available
                self.model_loaded = any(
                    self.config.model_name in model_name
                    for model_name in model_names
                )

                if not self.model_loaded:
                    logger.warning(f"Model {self.config.model_name} not found. Available models: {model_names}")

                self.last_health_check = current_time
                return self.model_loaded

        except Exception as e:
            logger.warning(f"Local LLM health check failed: {e}")
            self.model_loaded = False

        return False

    async def generate_dialogue(
        self,
        context: NPCInteractionContext,
        personality: PersonalityTraits,
        memories: List[MemoryItem],
        emotional_influence: Optional[Dict] = None,
    ) -> DialogueResponse:
        """Generate dialogue using local LLM."""
        if not await self._health_check():
            raise Exception("Local LLM not available")

        try:
            prompt = self._build_local_prompt(context, personality, memories, emotional_influence)

            start_time = time.time()

            # Make request to Ollama
            request_data = {
                "model": self.config.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": self.config.temperature,
                    "top_p": 0.9,
                    "max_tokens": self.config.max_tokens,
                    "stop": ["</response>", "\n\n---", "Human:", "User:"],
                }
            }

            response = await self.client.post(
                f"{self.config.ollama_base_url}/api/generate",
                json=request_data
            )

            if response.status_code != 200:
                raise Exception(f"Ollama request failed: {response.status_code}")

            result = response.json()
            generated_text = result.get("response", "")

            # Parse the response
            dialogue_response = self._parse_local_response(generated_text, personality, context)

            generation_time = time.time() - start_time
            logger.info(f"Local LLM generated dialogue in {generation_time:.2f}s")

            return dialogue_response

        except Exception as e:
            logger.error(f"Local LLM generation failed: {e}")
            # Fallback to simple response
            return self._create_fallback_response(context, personality)

    def _build_local_prompt(
        self,
        context: NPCInteractionContext,
        personality: PersonalityTraits,
        memories: List[MemoryItem],
        emotional_influence: Optional[Dict] = None,
    ) -> str:
        """Build a prompt optimized for local LLM."""
        # Simplify personality description for local models
        personality_traits = []
        if personality.friendliness > 0.6:
            personality_traits.append("friendly")
        if personality.curiosity > 0.6:
            personality_traits.append("curious")
        if personality.verbosity > 0.6:
            personality_traits.append("talkative")
        elif personality.verbosity < 0.4:
            personality_traits.append("quiet")
        if personality.humor > 0.6:
            personality_traits.append("humorous")

        personality_desc = ", ".join(personality_traits) if personality_traits else "neutral"

        # Add emotional state if available
        emotion_desc = ""
        if emotional_influence:
            emotion = emotional_influence.get("primary_emotion", "neutral")
            intensity = emotional_influence.get("emotion_intensity", 0.5)
            emotion_desc = f", currently feeling {emotion} ({intensity:.1f}/1.0)"

        # Format memories briefly
        memory_text = "No previous interactions." if not memories else "Previous interactions: " + "; ".join([
            memory.content[:60] + "..." if len(memory.content) > 60 else memory.content
            for memory in memories[:3]
        ])

        # Build concise prompt
        prompt = f"""You are an NPC in a Pokemon-style game called Tuxemon. Generate a short, natural response.

Character: {personality_desc}{emotion_desc} personality
Memories: {memory_text}
Context: {context.interaction_type} at {context.time_of_day}, relationship level {context.relationship_level:.1f}/1.0

Rules:
- Keep response under 100 words
- Reference memories if relevant
- Match your personality
- Use friendly, appropriate language
- Respond in JSON format

Required format:
{{"text": "your response here", "emotion": "happy|neutral|excited|sad", "relationship_change": 0.0}}

Response:"""

        return prompt

    def _parse_local_response(
        self,
        generated_text: str,
        personality: PersonalityTraits,
        context: NPCInteractionContext,
    ) -> DialogueResponse:
        """Parse response from local LLM."""
        try:
            # Try to extract JSON from the response
            text = generated_text.strip()

            # Look for JSON block
            if "{" in text and "}" in text:
                start_idx = text.find("{")
                end_idx = text.rfind("}") + 1
                json_text = text[start_idx:end_idx]

                try:
                    parsed = json.loads(json_text)
                    return DialogueResponse(
                        text=parsed.get("text", "Hello there!")[:200],  # Limit length
                        emotion=parsed.get("emotion", "neutral"),
                        relationship_change=float(parsed.get("relationship_change", 0.05)),
                        actions=parsed.get("actions", []),
                        triggers_battle=parsed.get("triggers_battle", False),
                    )
                except json.JSONDecodeError:
                    pass

            # Fallback: treat as plain text
            clean_text = text.replace('"', '').replace('{', '').replace('}', '').strip()
            if clean_text and len(clean_text) > 10:
                return DialogueResponse(
                    text=clean_text[:150],  # Limit length
                    emotion="neutral",
                    relationship_change=0.05,
                )

        except Exception as e:
            logger.warning(f"Failed to parse local LLM response: {e}")

        # Final fallback
        return self._create_fallback_response(context, personality)

    def _create_fallback_response(
        self,
        context: NPCInteractionContext,
        personality: PersonalityTraits,
    ) -> DialogueResponse:
        """Create a simple fallback response when local LLM fails."""
        if context.relationship_level > 0.5:
            responses = [
                "Good to see you again!",
                "How have you been?",
                "Nice to chat with you!",
            ]
        else:
            responses = [
                "Hello there!",
                "How can I help you?",
                "Welcome to our town!",
            ]

        import random
        text = random.choice(responses)

        if personality.verbosity > 0.7:
            text += " How's your adventure going?"

        return DialogueResponse(
            text=text,
            emotion="happy" if personality.friendliness > 0.5 else "neutral",
            relationship_change=0.1,
        )

    async def close(self):
        """Close the local LLM client."""
        if self.client:
            await self.client.aclose()


class HybridLLMManager:
    """Manages both Claude API and local LLM with intelligent fallback."""

    def __init__(self, claude_manager, local_manager: LocalLLMManager):
        self.claude_manager = claude_manager
        self.local_manager = local_manager
        self.use_local_ratio = 0.8  # Use local LLM 80% of the time

    async def generate_dialogue(
        self,
        npc_id: str,
        context: NPCInteractionContext,
        personality: PersonalityTraits,
        memories: List[MemoryItem],
        force_claude: bool = False,
        emotional_influence: Optional[Dict] = None,
    ) -> DialogueResponse:
        """Generate dialogue using hybrid approach."""
        use_local = (
            not force_claude and
            self.local_manager.config.enabled and
            await self.local_manager._health_check() and
            self._should_use_local(context, personality, memories)
        )

        if use_local:
            try:
                # Try local LLM first
                response = await self.local_manager.generate_dialogue(context, personality, memories, emotional_influence)

                # Quality check - if response seems too generic, fall back to Claude
                if self._is_response_too_generic(response, memories, context):
                    logger.info("Local response too generic, falling back to Claude")
                    return await self.claude_manager.generate_dialogue(npc_id, context, personality, memories)

                logger.info("Used local LLM for dialogue generation")
                return response

            except Exception as e:
                logger.warning(f"Local LLM failed, falling back to Claude: {e}")

        # Use Claude API
        return await self.claude_manager.generate_dialogue(npc_id, context, personality, memories)

    def _should_use_local(
        self,
        context: NPCInteractionContext,
        personality: PersonalityTraits,
        memories: List[MemoryItem],
    ) -> bool:
        """Decide whether to use local LLM based on complexity."""
        import random

        # Always use Claude for high-relationship or story-critical NPCs
        if context.relationship_level > 0.8:
            return False

        # Use Claude for complex interactions with many memories
        if len(memories) > 3 and any(m.importance > 0.8 for m in memories):
            return False

        # Use Claude for battle-related interactions
        if context.interaction_type == "battle":
            return False

        # Use random selection within the ratio
        return random.random() < self.use_local_ratio

    def _is_response_too_generic(
        self,
        response: DialogueResponse,
        memories: List[MemoryItem],
        context: NPCInteractionContext,
    ) -> bool:
        """Check if the response is too generic and should use Claude instead."""
        # If we have memories but response doesn't reference them
        if memories and context.relationship_level > 0.3:
            memory_keywords = set()
            for memory in memories[:2]:
                words = memory.content.lower().split()
                memory_keywords.update([w for w in words if len(w) > 4])

            response_words = set(response.text.lower().split())
            memory_overlap = len(memory_keywords.intersection(response_words))

            # If no memory keywords in response, it might be too generic
            if memory_overlap == 0 and len(memory_keywords) > 0:
                return True

        # Check for overly generic phrases
        generic_phrases = [
            "how can i help",
            "hello there",
            "how are you",
            "nice to see you",
            "welcome",
        ]

        response_lower = response.text.lower()
        generic_count = sum(1 for phrase in generic_phrases if phrase in response_lower)

        # If response is mostly generic phrases and we have context, it's probably too generic
        return generic_count >= 2 and (memories or context.relationship_level > 0.2)


# Global local LLM manager instance
local_llm_manager = LocalLLMManager()