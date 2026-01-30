# Load Testing Suite for AI-Powered Tuxemon
# Austin Kidwell | Intellegix | Mobile-First Pokemon-Style Game

import asyncio
import aiohttp
import time
import json
import statistics
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from uuid import uuid4
import random
from loguru import logger


@dataclass
class LoadTestConfig:
    """Configuration for load testing."""
    base_url: str = "http://localhost:8000"
    concurrent_users: int = 100
    test_duration_seconds: int = 300  # 5 minutes
    ramp_up_seconds: int = 60  # 1 minute to reach full load
    api_timeout_seconds: int = 10

    # Test scenarios weights (should sum to 1.0)
    scenarios: Dict[str, float] = None

    def __post_init__(self):
        if self.scenarios is None:
            self.scenarios = {
                "auth_and_basic": 0.3,      # Login, get world state
                "npc_interaction": 0.25,     # Dialogue with NPCs
                "game_actions": 0.2,         # Move, inventory, shop
                "battle_simulation": 0.15,   # Combat scenarios
                "ai_heavy": 0.1              # AI-intensive operations
            }


@dataclass
class TestResult:
    """Individual test result."""
    scenario: str
    endpoint: str
    method: str
    status_code: int
    response_time_ms: int
    success: bool
    error_message: Optional[str] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class LoadTestResults:
    """Aggregated load test results."""
    config: LoadTestConfig
    start_time: datetime
    end_time: datetime
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time_ms: float
    p50_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    max_response_time_ms: int
    requests_per_second: float
    errors_by_endpoint: Dict[str, int]
    cost_analysis: Dict[str, float]

    @property
    def success_rate(self) -> float:
        return (self.successful_requests / self.total_requests) * 100 if self.total_requests > 0 else 0


class LoadTestClient:
    """Individual user simulation client."""

    def __init__(self, client_id: int, config: LoadTestConfig):
        self.client_id = client_id
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self.auth_token: Optional[str] = None
        self.player_id: Optional[str] = None
        self.results: List[TestResult] = []

    async def initialize(self):
        """Initialize the client session."""
        timeout = aiohttp.ClientTimeout(total=self.config.api_timeout_seconds)
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            headers={"Content-Type": "application/json"}
        )

    async def cleanup(self):
        """Clean up the client session."""
        if self.session:
            await self.session.close()

    async def authenticate(self) -> bool:
        """Simulate user authentication."""
        try:
            # Create a test user
            username = f"loadtest_user_{self.client_id}_{random.randint(1000, 9999)}"
            email = f"{username}@loadtest.example.com"
            password = "LoadTest123!"

            # Register user
            register_data = {
                "username": username,
                "email": email,
                "password": password,
                "confirm_password": password
            }

            start_time = time.time()
            async with self.session.post(
                f"{self.config.base_url}/api/v1/auth/register",
                json=register_data
            ) as response:
                response_time = int((time.time() - start_time) * 1000)

                if response.status == 201:
                    # Now login
                    login_data = {"username": username, "password": password}

                    start_time = time.time()
                    async with self.session.post(
                        f"{self.config.base_url}/api/v1/auth/login",
                        json=login_data
                    ) as login_response:
                        login_response_time = int((time.time() - start_time) * 1000)

                        if login_response.status == 200:
                            data = await login_response.json()
                            self.auth_token = data.get("access_token")
                            self.player_id = data.get("player_id")

                            # Add auth header to session
                            self.session.headers.update({
                                "Authorization": f"Bearer {self.auth_token}"
                            })

                            self.results.append(TestResult(
                                scenario="auth",
                                endpoint="/auth/register",
                                method="POST",
                                status_code=response.status,
                                response_time_ms=response_time,
                                success=True
                            ))

                            self.results.append(TestResult(
                                scenario="auth",
                                endpoint="/auth/login",
                                method="POST",
                                status_code=login_response.status,
                                response_time_ms=login_response_time,
                                success=True
                            ))

                            return True

                        self.results.append(TestResult(
                            scenario="auth",
                            endpoint="/auth/login",
                            method="POST",
                            status_code=login_response.status,
                            response_time_ms=login_response_time,
                            success=False,
                            error_message="Login failed"
                        ))

                self.results.append(TestResult(
                    scenario="auth",
                    endpoint="/auth/register",
                    method="POST",
                    status_code=response.status,
                    response_time_ms=response_time,
                    success=False,
                    error_message="Registration failed"
                ))

        except Exception as e:
            self.results.append(TestResult(
                scenario="auth",
                endpoint="/auth/register",
                method="POST",
                status_code=0,
                response_time_ms=self.config.api_timeout_seconds * 1000,
                success=False,
                error_message=str(e)
            ))

        return False

    async def run_scenario_auth_and_basic(self):
        """Basic authentication and world state scenarios."""
        # Get world state
        await self._make_request(
            "GET", "/api/v1/game/world", "auth_and_basic", "world_state"
        )

        # Get player state
        await self._make_request(
            "GET", "/api/v1/game/player", "auth_and_basic", "player_state"
        )

        # Get monster species (paginated)
        await self._make_request(
            "GET", "/api/v1/game/monsters/species?page=1&per_page=20",
            "auth_and_basic", "monster_species"
        )

    async def run_scenario_npc_interaction(self):
        """NPC dialogue and interaction scenarios."""
        # Get nearby NPCs
        npcs_response = await self._make_request(
            "GET", "/api/v1/npcs/nearby", "npc_interaction", "nearby_npcs"
        )

        if npcs_response and npcs_response.get("npcs"):
            # Interact with a random NPC
            npc = random.choice(npcs_response["npcs"])
            npc_id = npc.get("id")

            if npc_id:
                interaction_data = {
                    "interaction_type": random.choice(["dialogue", "greeting"])
                }

                await self._make_request(
                    "POST", f"/api/v1/npcs/{npc_id}/interact",
                    "npc_interaction", "npc_dialogue", json_data=interaction_data
                )

    async def run_scenario_game_actions(self):
        """Game action scenarios (move, inventory, shop)."""
        # Move player
        move_data = {
            "new_x": random.randint(0, 50),
            "new_y": random.randint(0, 50)
        }
        await self._make_request(
            "POST", "/api/v1/game/move", "game_actions", "player_move",
            json_data=move_data
        )

        # Get inventory (paginated)
        await self._make_request(
            "GET", "/api/v1/inventory/?page=1&per_page=20",
            "game_actions", "inventory"
        )

        # Save game state
        save_data = {
            "current_map": "starter_town",
            "position_x": move_data["new_x"],
            "position_y": move_data["new_y"],
            "story_progress": {},
            "play_time_seconds": random.randint(300, 3600)
        }
        await self._make_request(
            "POST", "/api/v1/game/save", "game_actions", "save_game",
            json_data=save_data
        )

    async def run_scenario_battle_simulation(self):
        """Battle and combat scenarios."""
        # Initialize a mock battle
        battle_data = {
            "opponent_type": "npc",
            "opponent_id": str(uuid4())
        }

        await self._make_request(
            "POST", "/api/v1/combat/initiate", "battle_simulation", "initiate_battle",
            json_data=battle_data
        )

    async def run_scenario_ai_heavy(self):
        """AI-intensive scenarios for cost and performance testing."""
        # Get gossip statistics
        await self._make_request(
            "GET", "/api/v1/gossip/stats", "ai_heavy", "gossip_stats"
        )

        # Check cost tracker stats
        await self._make_request(
            "GET", "/api/v1/admin/ai/cost-stats", "ai_heavy", "cost_stats"
        )

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        scenario: str,
        operation: str,
        json_data: Optional[Dict] = None
    ) -> Optional[Dict]:
        """Make an HTTP request and record results."""
        try:
            url = f"{self.config.base_url}{endpoint}"
            start_time = time.time()

            if method.upper() == "GET":
                async with self.session.get(url) as response:
                    response_time = int((time.time() - start_time) * 1000)
                    success = response.status < 400

                    result = TestResult(
                        scenario=scenario,
                        endpoint=endpoint,
                        method=method,
                        status_code=response.status,
                        response_time_ms=response_time,
                        success=success,
                        error_message=None if success else f"HTTP {response.status}"
                    )
                    self.results.append(result)

                    if success:
                        try:
                            return await response.json()
                        except:
                            return None

            elif method.upper() == "POST":
                async with self.session.post(url, json=json_data) as response:
                    response_time = int((time.time() - start_time) * 1000)
                    success = response.status < 400

                    result = TestResult(
                        scenario=scenario,
                        endpoint=endpoint,
                        method=method,
                        status_code=response.status,
                        response_time_ms=response_time,
                        success=success,
                        error_message=None if success else f"HTTP {response.status}"
                    )
                    self.results.append(result)

                    if success:
                        try:
                            return await response.json()
                        except:
                            return None

        except Exception as e:
            result = TestResult(
                scenario=scenario,
                endpoint=endpoint,
                method=method,
                status_code=0,
                response_time_ms=self.config.api_timeout_seconds * 1000,
                success=False,
                error_message=str(e)
            )
            self.results.append(result)

        return None

    async def run_test_session(self):
        """Run a complete test session."""
        await self.initialize()

        try:
            # Authenticate first
            if not await self.authenticate():
                logger.error(f"Client {self.client_id} failed to authenticate")
                return

            # Calculate how long to run
            end_time = time.time() + self.config.test_duration_seconds

            while time.time() < end_time:
                # Select scenario based on weights
                scenario = random.choices(
                    list(self.config.scenarios.keys()),
                    weights=list(self.config.scenarios.values())
                )[0]

                # Run the selected scenario
                if scenario == "auth_and_basic":
                    await self.run_scenario_auth_and_basic()
                elif scenario == "npc_interaction":
                    await self.run_scenario_npc_interaction()
                elif scenario == "game_actions":
                    await self.run_scenario_game_actions()
                elif scenario == "battle_simulation":
                    await self.run_scenario_battle_simulation()
                elif scenario == "ai_heavy":
                    await self.run_scenario_ai_heavy()

                # Wait before next request (simulate user think time)
                await asyncio.sleep(random.uniform(1, 3))

        except Exception as e:
            logger.error(f"Client {self.client_id} error: {e}")
        finally:
            await self.cleanup()


class LoadTestRunner:
    """Main load testing orchestrator."""

    def __init__(self, config: LoadTestConfig):
        self.config = config
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.all_results: List[TestResult] = []

    async def run(self) -> LoadTestResults:
        """Run the complete load test suite."""
        logger.info(f"🚀 Starting load test with {self.config.concurrent_users} concurrent users")
        logger.info(f"   Duration: {self.config.test_duration_seconds}s")
        logger.info(f"   Ramp-up: {self.config.ramp_up_seconds}s")
        logger.info(f"   Target: {self.config.base_url}")

        self.start_time = datetime.utcnow()

        # Create clients
        clients = [
            LoadTestClient(i, self.config)
            for i in range(self.config.concurrent_users)
        ]

        # Stagger client start times for ramp-up
        tasks = []
        ramp_delay = self.config.ramp_up_seconds / self.config.concurrent_users

        for i, client in enumerate(clients):
            # Delay start based on ramp-up schedule
            start_delay = i * ramp_delay
            task = asyncio.create_task(self._run_client_with_delay(client, start_delay))
            tasks.append(task)

        # Wait for all clients to complete
        await asyncio.gather(*tasks, return_exceptions=True)

        # Collect all results
        for client in clients:
            self.all_results.extend(client.results)

        self.end_time = datetime.utcnow()

        # Analyze results
        return self._analyze_results()

    async def _run_client_with_delay(self, client: LoadTestClient, delay: float):
        """Run a client with initial delay for ramp-up."""
        await asyncio.sleep(delay)
        await client.run_test_session()

    def _analyze_results(self) -> LoadTestResults:
        """Analyze and aggregate test results."""
        if not self.all_results:
            raise ValueError("No test results to analyze")

        successful_results = [r for r in self.all_results if r.success]
        failed_results = [r for r in self.all_results if not r.success]

        # Calculate response time statistics
        response_times = [r.response_time_ms for r in successful_results]

        if response_times:
            avg_response_time = statistics.mean(response_times)
            p50 = statistics.median(response_times)
            p95 = statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else max(response_times)
            p99 = statistics.quantiles(response_times, n=100)[98] if len(response_times) > 100 else max(response_times)
            max_response_time = max(response_times)
        else:
            avg_response_time = p50 = p95 = p99 = max_response_time = 0

        # Calculate requests per second
        duration = (self.end_time - self.start_time).total_seconds()
        rps = len(self.all_results) / duration if duration > 0 else 0

        # Analyze errors by endpoint
        errors_by_endpoint = {}
        for result in failed_results:
            endpoint = result.endpoint
            errors_by_endpoint[endpoint] = errors_by_endpoint.get(endpoint, 0) + 1

        # Estimate cost impact
        cost_analysis = self._estimate_cost_impact()

        return LoadTestResults(
            config=self.config,
            start_time=self.start_time,
            end_time=self.end_time,
            total_requests=len(self.all_results),
            successful_requests=len(successful_results),
            failed_requests=len(failed_results),
            avg_response_time_ms=avg_response_time,
            p50_response_time_ms=p50,
            p95_response_time_ms=p95,
            p99_response_time_ms=p99,
            max_response_time_ms=max_response_time,
            requests_per_second=rps,
            errors_by_endpoint=errors_by_endpoint,
            cost_analysis=cost_analysis
        )

    def _estimate_cost_impact(self) -> Dict[str, float]:
        """Estimate AI cost impact from the load test."""
        ai_heavy_requests = [r for r in self.all_results if r.scenario == "ai_heavy"]
        npc_interaction_requests = [r for r in self.all_results if r.scenario == "npc_interaction"]

        # Rough cost estimates
        estimated_claude_calls = len(npc_interaction_requests) * 0.2  # 20% use Claude
        estimated_local_llm_calls = len(npc_interaction_requests) * 0.8  # 80% use local

        estimated_cost = (estimated_claude_calls * 0.02) + (estimated_local_llm_calls * 0.001)

        return {
            "estimated_total_cost": estimated_cost,
            "estimated_claude_calls": estimated_claude_calls,
            "estimated_local_calls": estimated_local_llm_calls,
            "projected_daily_cost": estimated_cost * (86400 / self.config.test_duration_seconds),
            "projected_monthly_cost": estimated_cost * (86400 / self.config.test_duration_seconds) * 30
        }

    def print_results(self, results: LoadTestResults):
        """Print detailed test results."""
        print("\n" + "="*80)
        print("🎯 LOAD TEST RESULTS")
        print("="*80)

        print(f"📊 Test Configuration:")
        print(f"   Concurrent Users: {results.config.concurrent_users}")
        print(f"   Test Duration: {results.config.test_duration_seconds}s")
        print(f"   Target URL: {results.config.base_url}")

        print(f"\n📈 Performance Metrics:")
        print(f"   Total Requests: {results.total_requests:,}")
        print(f"   Success Rate: {results.success_rate:.2f}%")
        print(f"   Requests/Second: {results.requests_per_second:.2f}")
        print(f"   Average Response Time: {results.avg_response_time_ms:.0f}ms")
        print(f"   P50 Response Time: {results.p50_response_time_ms:.0f}ms")
        print(f"   P95 Response Time: {results.p95_response_time_ms:.0f}ms")
        print(f"   P99 Response Time: {results.p99_response_time_ms:.0f}ms")
        print(f"   Max Response Time: {results.max_response_time_ms:.0f}ms")

        if results.errors_by_endpoint:
            print(f"\n❌ Errors by Endpoint:")
            for endpoint, count in sorted(results.errors_by_endpoint.items(), key=lambda x: x[1], reverse=True):
                print(f"   {endpoint}: {count} errors")

        print(f"\n💰 Cost Analysis:")
        cost = results.cost_analysis
        print(f"   Estimated Test Cost: ${cost['estimated_total_cost']:.4f}")
        print(f"   Claude API Calls: {cost['estimated_claude_calls']:.0f}")
        print(f"   Local LLM Calls: {cost['estimated_local_calls']:.0f}")
        print(f"   Projected Daily Cost: ${cost['projected_daily_cost']:.2f}")
        print(f"   Projected Monthly Cost: ${cost['projected_monthly_cost']:.2f}")

        # Performance assessment
        print(f"\n🎯 Performance Assessment:")
        if results.success_rate >= 99.5:
            print("   ✅ SUCCESS RATE: Excellent (≥99.5%)")
        elif results.success_rate >= 95:
            print("   ⚠️  SUCCESS RATE: Good (≥95%)")
        else:
            print("   ❌ SUCCESS RATE: Poor (<95%)")

        if results.p95_response_time_ms <= 500:
            print("   ✅ RESPONSE TIME: Excellent P95 ≤500ms")
        elif results.p95_response_time_ms <= 1000:
            print("   ⚠️  RESPONSE TIME: Acceptable P95 ≤1000ms")
        else:
            print("   ❌ RESPONSE TIME: Poor P95 >1000ms")

        if results.requests_per_second >= 100:
            print("   ✅ THROUGHPUT: Excellent (≥100 RPS)")
        elif results.requests_per_second >= 50:
            print("   ⚠️  THROUGHPUT: Good (≥50 RPS)")
        else:
            print("   ❌ THROUGHPUT: Poor (<50 RPS)")

        print("="*80)


# Main execution
async def main():
    """Main load testing execution."""

    # Configuration for different test scenarios
    configs = {
        "quick": LoadTestConfig(
            concurrent_users=10,
            test_duration_seconds=60,
            ramp_up_seconds=10
        ),
        "standard": LoadTestConfig(
            concurrent_users=50,
            test_duration_seconds=180,
            ramp_up_seconds=30
        ),
        "heavy": LoadTestConfig(
            concurrent_users=100,
            test_duration_seconds=300,
            ramp_up_seconds=60
        ),
        "production": LoadTestConfig(
            concurrent_users=200,
            test_duration_seconds=600,
            ramp_up_seconds=120
        )
    }

    # Select configuration (you can change this)
    test_type = "standard"  # Change to "quick", "standard", "heavy", or "production"
    config = configs[test_type]

    print(f"🚀 Running {test_type} load test...")

    runner = LoadTestRunner(config)
    results = await runner.run()
    runner.print_results(results)

    # Save results to file
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"load_test_results_{test_type}_{timestamp}.json"

    results_dict = {
        "config": {
            "concurrent_users": config.concurrent_users,
            "test_duration_seconds": config.test_duration_seconds,
            "scenarios": config.scenarios
        },
        "results": {
            "start_time": results.start_time.isoformat(),
            "end_time": results.end_time.isoformat(),
            "total_requests": results.total_requests,
            "success_rate": results.success_rate,
            "avg_response_time_ms": results.avg_response_time_ms,
            "p95_response_time_ms": results.p95_response_time_ms,
            "requests_per_second": results.requests_per_second,
            "errors_by_endpoint": results.errors_by_endpoint,
            "cost_analysis": results.cost_analysis
        }
    }

    with open(filename, 'w') as f:
        json.dump(results_dict, f, indent=2)

    print(f"\n📄 Results saved to: {filename}")


if __name__ == "__main__":
    asyncio.run(main())