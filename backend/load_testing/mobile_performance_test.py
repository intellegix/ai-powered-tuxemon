# Mobile Performance Testing for AI-Powered Tuxemon
# Austin Kidwell | Intellegix | Mobile-First Pokemon-Style Game

import asyncio
import aiohttp
import time
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import random
from loguru import logger


@dataclass
class MobileTestScenario:
    """Mobile-specific test scenario."""
    name: str
    description: str
    api_calls: List[Tuple[str, str, Optional[Dict]]]  # method, endpoint, data
    expected_response_time_ms: int
    mobile_bandwidth_kbps: int  # Simulate mobile bandwidth
    network_latency_ms: int     # Simulate mobile latency


@dataclass
class MobilePerformanceResult:
    """Mobile performance test result."""
    scenario: str
    total_time_ms: int
    api_calls_count: int
    largest_response_kb: float
    total_data_transferred_kb: float
    battery_efficiency_score: float  # Lower is better
    user_experience_score: float     # Higher is better (1-100)
    performance_bottlenecks: List[str]


class MobilePerformanceTester:
    """Mobile performance testing simulator."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.auth_token: Optional[str] = None

        # Mobile network conditions
        self.network_conditions = {
            "3g": {"bandwidth_kbps": 384, "latency_ms": 300},
            "4g": {"bandwidth_kbps": 10000, "latency_ms": 100},
            "wifi": {"bandwidth_kbps": 50000, "latency_ms": 20},
            "poor_connection": {"bandwidth_kbps": 128, "latency_ms": 800}
        }

    async def initialize(self):
        """Initialize testing session."""
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(timeout=timeout)

        # Authenticate with a test account
        await self._authenticate()

    async def cleanup(self):
        """Clean up resources."""
        if self.session:
            await self.session.close()

    async def _authenticate(self):
        """Authenticate for testing."""
        try:
            # Create test user
            username = f"mobile_test_{random.randint(1000, 9999)}"
            email = f"{username}@mobiletest.com"
            password = "MobileTest123!"

            # Register
            register_data = {
                "username": username,
                "email": email,
                "password": password,
                "confirm_password": password
            }

            async with self.session.post(
                f"{self.base_url}/api/v1/auth/register",
                json=register_data
            ) as response:
                if response.status == 201:
                    # Login
                    login_data = {"username": username, "password": password}
                    async with self.session.post(
                        f"{self.base_url}/api/v1/auth/login",
                        json=login_data
                    ) as login_response:
                        if login_response.status == 200:
                            data = await login_response.json()
                            self.auth_token = data.get("access_token")
                            self.session.headers.update({
                                "Authorization": f"Bearer {self.auth_token}"
                            })
                            return True

        except Exception as e:
            logger.error(f"Authentication failed: {e}")

        return False

    def get_test_scenarios(self) -> List[MobileTestScenario]:
        """Get mobile test scenarios."""
        return [
            MobileTestScenario(
                name="cold_start",
                description="App cold start - first time user experience",
                api_calls=[
                    ("GET", "/api/v1/game/world", None),
                    ("GET", "/api/v1/game/player", None),
                    ("GET", "/api/v1/game/monsters/species?page=1&per_page=20", None)
                ],
                expected_response_time_ms=2000,
                mobile_bandwidth_kbps=4000,
                network_latency_ms=150
            ),

            MobileTestScenario(
                name="npc_conversation",
                description="AI dialogue interaction with NPC",
                api_calls=[
                    ("GET", "/api/v1/npcs/nearby", None),
                    ("POST", "/api/v1/npcs/{npc_id}/interact", {"interaction_type": "dialogue"})
                ],
                expected_response_time_ms=1500,
                mobile_bandwidth_kbps=4000,
                network_latency_ms=150
            ),

            MobileTestScenario(
                name="battle_sequence",
                description="Complete battle from initiation to conclusion",
                api_calls=[
                    ("POST", "/api/v1/combat/initiate", {"opponent_type": "npc"}),
                    ("POST", "/api/v1/combat/action", {"action_type": "attack", "target": "enemy"}),
                    ("GET", "/api/v1/combat/state/{battle_id}", None)
                ],
                expected_response_time_ms=1000,
                mobile_bandwidth_kbps=4000,
                network_latency_ms=150
            ),

            MobileTestScenario(
                name="inventory_management",
                description="Browse and manage inventory items",
                api_calls=[
                    ("GET", "/api/v1/inventory/?page=1&per_page=20", None),
                    ("POST", "/api/v1/inventory/use", {"item_slug": "health_potion", "target_monster_id": "test"}),
                    ("GET", "/api/v1/inventory/?page=1&per_page=20", None)
                ],
                expected_response_time_ms=800,
                mobile_bandwidth_kbps=4000,
                network_latency_ms=150
            ),

            MobileTestScenario(
                name="offline_sync",
                description="Sync after being offline (worst case)",
                api_calls=[
                    ("GET", "/api/v1/game/player", None),
                    ("POST", "/api/v1/game/save", {
                        "current_map": "test_map",
                        "position_x": 10,
                        "position_y": 15,
                        "story_progress": {},
                        "play_time_seconds": 1800
                    }),
                    ("GET", "/api/v1/game/world", None)
                ],
                expected_response_time_ms=1200,
                mobile_bandwidth_kbps=2000,  # Slower when syncing
                network_latency_ms=200
            ),

            MobileTestScenario(
                name="poor_connection",
                description="Gameplay under poor network conditions",
                api_calls=[
                    ("GET", "/api/v1/game/world", None),
                    ("POST", "/api/v1/game/move", {"new_x": 5, "new_y": 8}),
                    ("GET", "/api/v1/npcs/nearby", None)
                ],
                expected_response_time_ms=3000,
                mobile_bandwidth_kbps=128,
                network_latency_ms=800
            ),

            MobileTestScenario(
                name="ai_heavy_load",
                description="Multiple AI operations in sequence",
                api_calls=[
                    ("GET", "/api/v1/gossip/stats", None),
                    ("POST", "/api/v1/npcs/{npc_id}/interact", {"interaction_type": "dialogue"}),
                    ("GET", "/api/v1/gossip/player/{player_id}/reputation?npc_id={npc_id}", None),
                    ("POST", "/api/v1/npcs/{npc_id}/interact", {"interaction_type": "greeting"})
                ],
                expected_response_time_ms=2500,
                mobile_bandwidth_kbps=4000,
                network_latency_ms=150
            )
        ]

    async def run_scenario(
        self,
        scenario: MobileTestScenario,
        network_condition: str = "4g"
    ) -> MobilePerformanceResult:
        """Run a specific mobile test scenario."""
        logger.info(f"🧪 Running mobile scenario: {scenario.name}")

        network = self.network_conditions[network_condition]
        start_time = time.time()
        total_data_kb = 0.0
        largest_response_kb = 0.0
        api_calls_made = 0
        bottlenecks = []

        # Simulate network latency
        await asyncio.sleep(network["latency_ms"] / 1000)

        try:
            for method, endpoint, data in scenario.api_calls:
                call_start = time.time()

                # Handle dynamic endpoints
                if "{npc_id}" in endpoint:
                    # Get a real NPC ID first
                    npc_id = await self._get_test_npc_id()
                    if npc_id:
                        endpoint = endpoint.replace("{npc_id}", npc_id)
                    else:
                        continue

                if "{player_id}" in endpoint:
                    endpoint = endpoint.replace("{player_id}", "test-player-id")

                if "{battle_id}" in endpoint:
                    endpoint = endpoint.replace("{battle_id}", "test-battle-id")

                # Make the API call
                response_size = await self._make_mobile_api_call(
                    method, endpoint, data, network
                )

                call_time = (time.time() - call_start) * 1000

                if response_size:
                    response_kb = response_size / 1024
                    total_data_kb += response_kb
                    largest_response_kb = max(largest_response_kb, response_kb)

                api_calls_made += 1

                # Check for performance issues
                if call_time > 2000:
                    bottlenecks.append(f"Slow API call: {endpoint} ({call_time:.0f}ms)")

                # Simulate network bandwidth limitations
                if response_size:
                    transfer_time = (response_size * 8) / (network["bandwidth_kbps"] * 1000)
                    await asyncio.sleep(transfer_time)

        except Exception as e:
            logger.error(f"Scenario failed: {e}")
            bottlenecks.append(f"API failure: {str(e)}")

        total_time = (time.time() - start_time) * 1000

        # Calculate performance scores
        battery_score = self._calculate_battery_score(
            total_time, api_calls_made, total_data_kb
        )

        ux_score = self._calculate_ux_score(
            total_time, scenario.expected_response_time_ms, len(bottlenecks)
        )

        # Check for additional bottlenecks
        if total_time > scenario.expected_response_time_ms * 1.5:
            bottlenecks.append("Overall scenario too slow")

        if total_data_kb > 500:  # 500KB threshold for mobile
            bottlenecks.append("Excessive data usage")

        return MobilePerformanceResult(
            scenario=scenario.name,
            total_time_ms=int(total_time),
            api_calls_count=api_calls_made,
            largest_response_kb=largest_response_kb,
            total_data_transferred_kb=total_data_kb,
            battery_efficiency_score=battery_score,
            user_experience_score=ux_score,
            performance_bottlenecks=bottlenecks
        )

    async def _get_test_npc_id(self) -> Optional[str]:
        """Get a test NPC ID for dynamic endpoints."""
        try:
            async with self.session.get(f"{self.base_url}/api/v1/npcs/nearby") as response:
                if response.status == 200:
                    data = await response.json()
                    npcs = data.get("npcs", [])
                    if npcs:
                        return npcs[0].get("id")
        except:
            pass
        return "test-npc-id"  # Fallback

    async def _make_mobile_api_call(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict],
        network: Dict
    ) -> Optional[int]:
        """Make an API call with mobile network simulation."""
        try:
            url = f"{self.base_url}{endpoint}"

            # Add mobile user agent
            headers = {"User-Agent": "TuxemonMobile/1.0 (iPhone; iOS 15.0)"}

            if method.upper() == "GET":
                async with self.session.get(url, headers=headers) as response:
                    content = await response.read()
                    return len(content) if response.status < 400 else None

            elif method.upper() == "POST":
                async with self.session.post(url, json=data, headers=headers) as response:
                    content = await response.read()
                    return len(content) if response.status < 400 else None

        except Exception as e:
            logger.warning(f"API call failed: {endpoint} - {e}")

        return None

    def _calculate_battery_score(
        self,
        total_time_ms: float,
        api_calls: int,
        data_kb: float
    ) -> float:
        """Calculate battery efficiency score (lower is better)."""
        # Battery drain factors:
        # - Time with screen on
        # - Network activity
        # - Number of API calls (CPU usage)
        # - Data transfer (radio usage)

        base_score = 10.0  # Base battery usage
        time_factor = (total_time_ms / 1000) * 2  # 2 points per second
        api_factor = api_calls * 1.5  # 1.5 points per API call
        data_factor = data_kb * 0.01  # 0.01 points per KB

        return base_score + time_factor + api_factor + data_factor

    def _calculate_ux_score(
        self,
        actual_time_ms: float,
        expected_time_ms: int,
        bottleneck_count: int
    ) -> float:
        """Calculate user experience score (higher is better, 1-100)."""
        base_score = 100.0

        # Performance penalty
        if actual_time_ms > expected_time_ms:
            performance_ratio = actual_time_ms / expected_time_ms
            performance_penalty = min(50, (performance_ratio - 1) * 30)
            base_score -= performance_penalty

        # Bottleneck penalties
        bottleneck_penalty = min(30, bottleneck_count * 10)
        base_score -= bottleneck_penalty

        return max(1.0, base_score)

    async def run_full_mobile_test_suite(self) -> Dict[str, MobilePerformanceResult]:
        """Run the complete mobile performance test suite."""
        await self.initialize()

        results = {}
        scenarios = self.get_test_scenarios()

        logger.info(f"🚀 Running {len(scenarios)} mobile performance scenarios")

        try:
            for scenario in scenarios:
                # Test under different network conditions
                network_condition = "3g" if scenario.name == "poor_connection" else "4g"
                result = await self.run_scenario(scenario, network_condition)
                results[scenario.name] = result

                # Brief pause between scenarios
                await asyncio.sleep(1)

        finally:
            await self.cleanup()

        return results

    def print_mobile_test_results(self, results: Dict[str, MobilePerformanceResult]):
        """Print mobile test results with mobile-specific metrics."""
        print("\n" + "="*80)
        print("📱 MOBILE PERFORMANCE TEST RESULTS")
        print("="*80)

        total_scenarios = len(results)
        excellent_ux = sum(1 for r in results.values() if r.user_experience_score >= 90)
        good_ux = sum(1 for r in results.values() if 70 <= r.user_experience_score < 90)
        poor_ux = sum(1 for r in results.values() if r.user_experience_score < 70)

        print(f"📊 Test Summary:")
        print(f"   Total Scenarios: {total_scenarios}")
        print(f"   Excellent UX: {excellent_ux} ({excellent_ux/total_scenarios*100:.1f}%)")
        print(f"   Good UX: {good_ux} ({good_ux/total_scenarios*100:.1f}%)")
        print(f"   Poor UX: {poor_ux} ({poor_ux/total_scenarios*100:.1f}%)")

        print(f"\n📱 Detailed Results:")

        for scenario_name, result in results.items():
            status_icon = "✅" if result.user_experience_score >= 80 else "⚠️" if result.user_experience_score >= 60 else "❌"

            print(f"\n{status_icon} {scenario_name.upper().replace('_', ' ')}")
            print(f"   Total Time: {result.total_time_ms}ms")
            print(f"   UX Score: {result.user_experience_score:.1f}/100")
            print(f"   Battery Score: {result.battery_efficiency_score:.1f} (lower better)")
            print(f"   API Calls: {result.api_calls_count}")
            print(f"   Data Transfer: {result.total_data_transferred_kb:.2f}KB")
            print(f"   Largest Response: {result.largest_response_kb:.2f}KB")

            if result.performance_bottlenecks:
                print(f"   Bottlenecks:")
                for bottleneck in result.performance_bottlenecks:
                    print(f"     - {bottleneck}")

        # Overall mobile readiness assessment
        print(f"\n🎯 Mobile Readiness Assessment:")

        avg_ux_score = sum(r.user_experience_score for r in results.values()) / len(results)
        avg_battery_score = sum(r.battery_efficiency_score for r in results.values()) / len(results)
        max_response_time = max(r.total_time_ms for r in results.values())
        total_data_usage = sum(r.total_data_transferred_kb for r in results.values())

        if avg_ux_score >= 85:
            print("   ✅ USER EXPERIENCE: Excellent")
        elif avg_ux_score >= 70:
            print("   ⚠️  USER EXPERIENCE: Good")
        else:
            print("   ❌ USER EXPERIENCE: Needs Improvement")

        if avg_battery_score <= 50:
            print("   ✅ BATTERY EFFICIENCY: Excellent")
        elif avg_battery_score <= 80:
            print("   ⚠️  BATTERY EFFICIENCY: Good")
        else:
            print("   ❌ BATTERY EFFICIENCY: Poor")

        if max_response_time <= 2000:
            print("   ✅ RESPONSIVENESS: Excellent")
        elif max_response_time <= 3000:
            print("   ⚠️  RESPONSIVENESS: Acceptable")
        else:
            print("   ❌ RESPONSIVENESS: Too Slow")

        if total_data_usage <= 200:
            print("   ✅ DATA USAGE: Efficient")
        elif total_data_usage <= 500:
            print("   ⚠️  DATA USAGE: Moderate")
        else:
            print("   ❌ DATA USAGE: Excessive")

        print("="*80)


# Main execution for mobile testing
async def main():
    """Run mobile performance tests."""
    tester = MobilePerformanceTester()
    results = await tester.run_full_mobile_test_suite()
    tester.print_mobile_test_results(results)

    # Save results
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"mobile_performance_results_{timestamp}.json"

    # Convert results to JSON-serializable format
    json_results = {}
    for name, result in results.items():
        json_results[name] = {
            "scenario": result.scenario,
            "total_time_ms": result.total_time_ms,
            "api_calls_count": result.api_calls_count,
            "largest_response_kb": result.largest_response_kb,
            "total_data_transferred_kb": result.total_data_transferred_kb,
            "battery_efficiency_score": result.battery_efficiency_score,
            "user_experience_score": result.user_experience_score,
            "performance_bottlenecks": result.performance_bottlenecks
        }

    with open(filename, 'w') as f:
        json.dump({
            "timestamp": timestamp,
            "results": json_results
        }, f, indent=2)

    print(f"\n📄 Mobile test results saved to: {filename}")


if __name__ == "__main__":
    asyncio.run(main())