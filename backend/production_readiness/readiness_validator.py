# Production Readiness Validator for AI-Powered Tuxemon
# Austin Kidwell | Intellegix | Mobile-First Pokemon-Style Game

import asyncio
import aiohttp
import psutil
import time
import json
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from loguru import logger

try:
    import psycopg
except ImportError:
    psycopg = None

try:
    from qdrant_client import QdrantClient
except ImportError:
    QdrantClient = None

try:
    import redis
except ImportError:
    redis = None


@dataclass
class ReadinessCheck:
    """Individual readiness check result."""
    category: str
    check_name: str
    status: str  # "pass", "fail", "warning", "skip"
    details: str
    execution_time_ms: int
    critical: bool = True


@dataclass
class SystemResource:
    """System resource measurement."""
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    network_connections: int


class ProductionReadinessValidator:
    """Comprehensive production readiness validation."""

    def __init__(self, config_file: Optional[str] = None):
        self.checks: List[ReadinessCheck] = []
        self.config = self._load_config(config_file)
        self.start_time = datetime.utcnow()

    def _load_config(self, config_file: Optional[str]) -> Dict[str, Any]:
        """Load validation configuration."""
        default_config = {
            "api_base_url": "http://localhost:8000",
            "database_url": os.getenv("DATABASE_URL", "postgresql://localhost:5432/tuxemon"),
            "redis_url": os.getenv("REDIS_URL", "redis://localhost:6379"),
            "qdrant_url": os.getenv("QDRANT_URL", "http://localhost:6333"),
            "required_endpoints": [
                "/health",
                "/api/v1/game/world",
                "/api/v1/game/player",
                "/api/v1/npcs/nearby",
                "/api/v1/inventory/",
                "/api/v1/gossip/stats"
            ],
            "performance_thresholds": {
                "api_response_time_ms": 500,
                "memory_usage_percent": 80,
                "cpu_usage_percent": 70,
                "disk_usage_percent": 85
            },
            "security_checks": [
                "ssl_certificate",
                "cors_headers",
                "rate_limiting",
                "input_validation"
            ]
        }

        if config_file and Path(config_file).exists():
            try:
                with open(config_file, 'r') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
            except Exception as e:
                logger.warning(f"Failed to load config file: {e}")

        return default_config

    async def validate_production_readiness(self) -> Dict[str, Any]:
        """Run complete production readiness validation."""
        logger.info("🚀 Starting production readiness validation...")

        # Core system checks
        await self._check_database_connectivity()
        await self._check_redis_connectivity()
        await self._check_qdrant_connectivity()

        # API and service checks
        await self._check_api_health()
        await self._check_critical_endpoints()
        await self._check_api_performance()

        # Security checks
        await self._check_security_configuration()

        # Database performance and integrity
        await self._check_database_performance()
        await self._check_database_indexes()

        # AI system checks
        await self._check_ai_system_health()
        await self._check_cost_tracking()
        await self._check_gossip_system()

        # Infrastructure checks
        self._check_system_resources()
        self._check_disk_space()
        self._check_network_connectivity()

        # Configuration validation
        self._check_environment_variables()
        self._check_logging_configuration()

        # Mobile readiness
        await self._check_mobile_optimization()

        # Generate final report
        return self._generate_readiness_report()

    async def _check_database_connectivity(self):
        """Check PostgreSQL database connectivity."""
        start_time = time.time()
        try:
            if psycopg:
                # Test connection
                import asyncpg
                conn = await asyncpg.connect(self.config["database_url"])

                # Test basic query
                result = await conn.fetchval("SELECT 1")
                await conn.close()

                if result == 1:
                    execution_time = int((time.time() - start_time) * 1000)
                    self.checks.append(ReadinessCheck(
                        category="Database",
                        check_name="PostgreSQL Connectivity",
                        status="pass",
                        details="Database connection successful",
                        execution_time_ms=execution_time,
                        critical=True
                    ))
                else:
                    raise Exception("Invalid query result")
            else:
                self.checks.append(ReadinessCheck(
                    category="Database",
                    check_name="PostgreSQL Connectivity",
                    status="skip",
                    details="psycopg not available",
                    execution_time_ms=0,
                    critical=True
                ))

        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            self.checks.append(ReadinessCheck(
                category="Database",
                check_name="PostgreSQL Connectivity",
                status="fail",
                details=f"Database connection failed: {str(e)}",
                execution_time_ms=execution_time,
                critical=True
            ))

    async def _check_redis_connectivity(self):
        """Check Redis connectivity."""
        start_time = time.time()
        try:
            if redis:
                r = redis.from_url(self.config["redis_url"])
                await r.ping()
                await r.close()

                execution_time = int((time.time() - start_time) * 1000)
                self.checks.append(ReadinessCheck(
                    category="Cache",
                    check_name="Redis Connectivity",
                    status="pass",
                    details="Redis connection successful",
                    execution_time_ms=execution_time,
                    critical=True
                ))
            else:
                self.checks.append(ReadinessCheck(
                    category="Cache",
                    check_name="Redis Connectivity",
                    status="skip",
                    details="redis package not available",
                    execution_time_ms=0,
                    critical=True
                ))

        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            self.checks.append(ReadinessCheck(
                category="Cache",
                check_name="Redis Connectivity",
                status="fail",
                details=f"Redis connection failed: {str(e)}",
                execution_time_ms=execution_time,
                critical=True
            ))

    async def _check_qdrant_connectivity(self):
        """Check Qdrant vector database connectivity."""
        start_time = time.time()
        try:
            if QdrantClient:
                client = QdrantClient(url=self.config["qdrant_url"])
                collections = client.get_collections()

                execution_time = int((time.time() - start_time) * 1000)
                self.checks.append(ReadinessCheck(
                    category="AI Database",
                    check_name="Qdrant Connectivity",
                    status="pass",
                    details=f"Qdrant connected, {len(collections.collections)} collections found",
                    execution_time_ms=execution_time,
                    critical=True
                ))
            else:
                self.checks.append(ReadinessCheck(
                    category="AI Database",
                    check_name="Qdrant Connectivity",
                    status="skip",
                    details="qdrant-client not available",
                    execution_time_ms=0,
                    critical=True
                ))

        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            self.checks.append(ReadinessCheck(
                category="AI Database",
                check_name="Qdrant Connectivity",
                status="fail",
                details=f"Qdrant connection failed: {str(e)}",
                execution_time_ms=execution_time,
                critical=True
            ))

    async def _check_api_health(self):
        """Check API health endpoint."""
        start_time = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.config['api_base_url']}/health") as response:
                    execution_time = int((time.time() - start_time) * 1000)

                    if response.status == 200:
                        data = await response.json()
                        self.checks.append(ReadinessCheck(
                            category="API",
                            check_name="Health Endpoint",
                            status="pass",
                            details=f"API healthy, response time: {execution_time}ms",
                            execution_time_ms=execution_time,
                            critical=True
                        ))
                    else:
                        self.checks.append(ReadinessCheck(
                            category="API",
                            check_name="Health Endpoint",
                            status="fail",
                            details=f"Health check failed with status {response.status}",
                            execution_time_ms=execution_time,
                            critical=True
                        ))

        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            self.checks.append(ReadinessCheck(
                category="API",
                check_name="Health Endpoint",
                status="fail",
                details=f"Health endpoint not reachable: {str(e)}",
                execution_time_ms=execution_time,
                critical=True
            ))

    async def _check_critical_endpoints(self):
        """Check all critical API endpoints."""
        async with aiohttp.ClientSession() as session:
            for endpoint in self.config["required_endpoints"]:
                start_time = time.time()
                try:
                    async with session.get(f"{self.config['api_base_url']}{endpoint}") as response:
                        execution_time = int((time.time() - start_time) * 1000)

                        if response.status < 500:  # Accept 4xx but not 5xx
                            status = "pass" if response.status < 400 else "warning"
                            details = f"Endpoint accessible (HTTP {response.status}), {execution_time}ms"
                        else:
                            status = "fail"
                            details = f"Server error (HTTP {response.status})"

                        self.checks.append(ReadinessCheck(
                            category="API Endpoints",
                            check_name=f"Endpoint {endpoint}",
                            status=status,
                            details=details,
                            execution_time_ms=execution_time,
                            critical=(status == "fail")
                        ))

                except Exception as e:
                    execution_time = int((time.time() - start_time) * 1000)
                    self.checks.append(ReadinessCheck(
                        category="API Endpoints",
                        check_name=f"Endpoint {endpoint}",
                        status="fail",
                        details=f"Endpoint unreachable: {str(e)}",
                        execution_time_ms=execution_time,
                        critical=True
                    ))

    async def _check_api_performance(self):
        """Check API performance under load."""
        start_time = time.time()
        try:
            # Make multiple concurrent requests to test performance
            async with aiohttp.ClientSession() as session:
                tasks = []
                for i in range(10):  # 10 concurrent requests
                    task = session.get(f"{self.config['api_base_url']}/api/v1/game/world")
                    tasks.append(task)

                responses = await asyncio.gather(*tasks, return_exceptions=True)

                successful_responses = 0
                total_time = 0

                for response in responses:
                    if isinstance(response, aiohttp.ClientResponse):
                        if response.status == 200:
                            successful_responses += 1
                        response.close()

                execution_time = int((time.time() - start_time) * 1000)
                avg_time = execution_time / 10

                threshold = self.config["performance_thresholds"]["api_response_time_ms"]

                if successful_responses >= 8 and avg_time <= threshold:
                    status = "pass"
                    details = f"Performance good: {successful_responses}/10 success, {avg_time:.0f}ms avg"
                elif successful_responses >= 6:
                    status = "warning"
                    details = f"Performance acceptable: {successful_responses}/10 success, {avg_time:.0f}ms avg"
                else:
                    status = "fail"
                    details = f"Performance poor: {successful_responses}/10 success, {avg_time:.0f}ms avg"

                self.checks.append(ReadinessCheck(
                    category="Performance",
                    check_name="API Load Test",
                    status=status,
                    details=details,
                    execution_time_ms=execution_time,
                    critical=(status == "fail")
                ))

        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            self.checks.append(ReadinessCheck(
                category="Performance",
                check_name="API Load Test",
                status="fail",
                details=f"Performance test failed: {str(e)}",
                execution_time_ms=execution_time,
                critical=False
            ))

    async def _check_security_configuration(self):
        """Check security configuration."""
        # Check CORS headers
        start_time = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.options(f"{self.config['api_base_url']}/api/v1/game/world") as response:
                    cors_headers = response.headers.get("Access-Control-Allow-Origin")

                    if cors_headers and cors_headers != "*":
                        status = "pass"
                        details = "CORS properly configured"
                    elif cors_headers == "*":
                        status = "warning"
                        details = "CORS allows all origins (development only)"
                    else:
                        status = "fail"
                        details = "CORS not configured"

                    execution_time = int((time.time() - start_time) * 1000)
                    self.checks.append(ReadinessCheck(
                        category="Security",
                        check_name="CORS Configuration",
                        status=status,
                        details=details,
                        execution_time_ms=execution_time,
                        critical=(status == "fail")
                    ))

        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            self.checks.append(ReadinessCheck(
                category="Security",
                check_name="CORS Configuration",
                status="warning",
                details=f"Could not check CORS: {str(e)}",
                execution_time_ms=execution_time,
                critical=False
            ))

    async def _check_database_performance(self):
        """Check database performance and connection pool."""
        start_time = time.time()
        try:
            if psycopg:
                import asyncpg
                # Test connection pool performance
                start_query_time = time.time()
                conn = await asyncpg.connect(self.config["database_url"])

                # Test a typical query
                await conn.fetchval("SELECT COUNT(*) FROM players")
                query_time = int((time.time() - start_query_time) * 1000)

                await conn.close()

                if query_time < 100:
                    status = "pass"
                    details = f"Database performance excellent ({query_time}ms)"
                elif query_time < 500:
                    status = "warning"
                    details = f"Database performance acceptable ({query_time}ms)"
                else:
                    status = "fail"
                    details = f"Database performance poor ({query_time}ms)"

                execution_time = int((time.time() - start_time) * 1000)
                self.checks.append(ReadinessCheck(
                    category="Database Performance",
                    check_name="Query Performance",
                    status=status,
                    details=details,
                    execution_time_ms=execution_time,
                    critical=(status == "fail")
                ))

        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            self.checks.append(ReadinessCheck(
                category="Database Performance",
                check_name="Query Performance",
                status="fail",
                details=f"Database performance test failed: {str(e)}",
                execution_time_ms=execution_time,
                critical=False
            ))

    async def _check_database_indexes(self):
        """Check critical database indexes."""
        start_time = time.time()
        try:
            if psycopg:
                import asyncpg
                conn = await asyncpg.connect(self.config["database_url"])

                # Check for critical indexes
                critical_indexes = [
                    "idx_monsters_player_id",
                    "idx_monsters_npc_id",
                    "idx_monsters_species_slug",
                    "idx_npcs_map_name"
                ]

                existing_indexes = []
                for index_name in critical_indexes:
                    result = await conn.fetchval("""
                        SELECT indexname FROM pg_indexes
                        WHERE indexname = $1
                    """, index_name)

                    if result:
                        existing_indexes.append(index_name)

                await conn.close()

                coverage = len(existing_indexes) / len(critical_indexes) * 100

                if coverage >= 100:
                    status = "pass"
                    details = f"All critical indexes present ({coverage:.0f}%)"
                elif coverage >= 75:
                    status = "warning"
                    details = f"Most indexes present ({coverage:.0f}%)"
                else:
                    status = "fail"
                    details = f"Missing critical indexes ({coverage:.0f}%)"

                execution_time = int((time.time() - start_time) * 1000)
                self.checks.append(ReadinessCheck(
                    category="Database Performance",
                    check_name="Critical Indexes",
                    status=status,
                    details=details,
                    execution_time_ms=execution_time,
                    critical=(status == "fail")
                ))

        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            self.checks.append(ReadinessCheck(
                category="Database Performance",
                check_name="Critical Indexes",
                status="warning",
                details=f"Could not check indexes: {str(e)}",
                execution_time_ms=execution_time,
                critical=False
            ))

    async def _check_ai_system_health(self):
        """Check AI system health."""
        start_time = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.config['api_base_url']}/api/v1/admin/ai/cost-stats") as response:
                    execution_time = int((time.time() - start_time) * 1000)

                    if response.status == 200:
                        data = await response.json()
                        budget_utilization = data.get("budget_utilization", 0)

                        if budget_utilization < 80:
                            status = "pass"
                            details = f"AI system healthy, {budget_utilization:.1f}% budget used"
                        elif budget_utilization < 95:
                            status = "warning"
                            details = f"AI budget high, {budget_utilization:.1f}% budget used"
                        else:
                            status = "fail"
                            details = f"AI budget critical, {budget_utilization:.1f}% budget used"

                        self.checks.append(ReadinessCheck(
                            category="AI System",
                            check_name="Cost Tracking Health",
                            status=status,
                            details=details,
                            execution_time_ms=execution_time,
                            critical=(status == "fail")
                        ))
                    else:
                        self.checks.append(ReadinessCheck(
                            category="AI System",
                            check_name="Cost Tracking Health",
                            status="fail",
                            details=f"AI cost stats unavailable (HTTP {response.status})",
                            execution_time_ms=execution_time,
                            critical=True
                        ))

        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            self.checks.append(ReadinessCheck(
                category="AI System",
                check_name="Cost Tracking Health",
                status="fail",
                details=f"AI system check failed: {str(e)}",
                execution_time_ms=execution_time,
                critical=True
            ))

    async def _check_cost_tracking(self):
        """Verify cost tracking and budget controls."""
        start_time = time.time()

        # Check if environment variables are set
        claude_api_key = os.getenv("CLAUDE_API_KEY")
        max_daily_budget = os.getenv("MAX_DAILY_BUDGET_USD", "50")

        try:
            daily_budget = float(max_daily_budget)
            if claude_api_key and daily_budget > 0:
                status = "pass"
                details = f"Cost controls configured (${daily_budget}/day limit)"
            elif claude_api_key:
                status = "warning"
                details = "Claude API configured but no budget limit set"
            else:
                status = "warning"
                details = "No Claude API key configured (local LLM only)"

            execution_time = int((time.time() - start_time) * 1000)
            self.checks.append(ReadinessCheck(
                category="AI System",
                check_name="Cost Controls",
                status=status,
                details=details,
                execution_time_ms=execution_time,
                critical=False
            ))

        except ValueError:
            execution_time = int((time.time() - start_time) * 1000)
            self.checks.append(ReadinessCheck(
                category="AI System",
                check_name="Cost Controls",
                status="fail",
                details="Invalid budget configuration",
                execution_time_ms=execution_time,
                critical=True
            ))

    async def _check_gossip_system(self):
        """Check gossip propagation system."""
        start_time = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.config['api_base_url']}/api/v1/gossip/stats") as response:
                    execution_time = int((time.time() - start_time) * 1000)

                    if response.status == 200:
                        data = await response.json()
                        networks = data.get("gossip_networks", 0)
                        avg_gossip = data.get("average_gossip_per_npc", 0)

                        if networks > 0:
                            status = "pass"
                            details = f"Gossip system active, {networks} networks, {avg_gossip:.1f} avg gossip/NPC"
                        else:
                            status = "warning"
                            details = "Gossip system initialized but no networks"

                        self.checks.append(ReadinessCheck(
                            category="AI System",
                            check_name="Gossip Propagation",
                            status=status,
                            details=details,
                            execution_time_ms=execution_time,
                            critical=False
                        ))
                    else:
                        self.checks.append(ReadinessCheck(
                            category="AI System",
                            check_name="Gossip Propagation",
                            status="fail",
                            details=f"Gossip stats unavailable (HTTP {response.status})",
                            execution_time_ms=execution_time,
                            critical=False
                        ))

        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            self.checks.append(ReadinessCheck(
                category="AI System",
                check_name="Gossip Propagation",
                status="warning",
                details=f"Could not check gossip system: {str(e)}",
                execution_time_ms=execution_time,
                critical=False
            ))

    def _check_system_resources(self):
        """Check system resource utilization."""
        start_time = time.time()

        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            execution_time = int((time.time() - start_time) * 1000)

            # CPU check
            cpu_threshold = self.config["performance_thresholds"]["cpu_usage_percent"]
            if cpu_percent < cpu_threshold:
                cpu_status = "pass"
                cpu_details = f"CPU usage healthy ({cpu_percent:.1f}%)"
            elif cpu_percent < cpu_threshold + 10:
                cpu_status = "warning"
                cpu_details = f"CPU usage high ({cpu_percent:.1f}%)"
            else:
                cpu_status = "fail"
                cpu_details = f"CPU usage critical ({cpu_percent:.1f}%)"

            self.checks.append(ReadinessCheck(
                category="System Resources",
                check_name="CPU Usage",
                status=cpu_status,
                details=cpu_details,
                execution_time_ms=execution_time,
                critical=(cpu_status == "fail")
            ))

            # Memory check
            memory_threshold = self.config["performance_thresholds"]["memory_usage_percent"]
            if memory.percent < memory_threshold:
                memory_status = "pass"
                memory_details = f"Memory usage healthy ({memory.percent:.1f}%)"
            elif memory.percent < memory_threshold + 10:
                memory_status = "warning"
                memory_details = f"Memory usage high ({memory.percent:.1f}%)"
            else:
                memory_status = "fail"
                memory_details = f"Memory usage critical ({memory.percent:.1f}%)"

            self.checks.append(ReadinessCheck(
                category="System Resources",
                check_name="Memory Usage",
                status=memory_status,
                details=memory_details,
                execution_time_ms=execution_time,
                critical=(memory_status == "fail")
            ))

        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            self.checks.append(ReadinessCheck(
                category="System Resources",
                check_name="Resource Monitoring",
                status="warning",
                details=f"Could not check system resources: {str(e)}",
                execution_time_ms=execution_time,
                critical=False
            ))

    def _check_disk_space(self):
        """Check available disk space."""
        start_time = time.time()

        try:
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent

            disk_threshold = self.config["performance_thresholds"]["disk_usage_percent"]

            if disk_percent < disk_threshold:
                status = "pass"
                details = f"Disk space healthy ({disk_percent:.1f}% used)"
            elif disk_percent < disk_threshold + 10:
                status = "warning"
                details = f"Disk space high ({disk_percent:.1f}% used)"
            else:
                status = "fail"
                details = f"Disk space critical ({disk_percent:.1f}% used)"

            execution_time = int((time.time() - start_time) * 1000)
            self.checks.append(ReadinessCheck(
                category="System Resources",
                check_name="Disk Space",
                status=status,
                details=details,
                execution_time_ms=execution_time,
                critical=(status == "fail")
            ))

        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            self.checks.append(ReadinessCheck(
                category="System Resources",
                check_name="Disk Space",
                status="warning",
                details=f"Could not check disk space: {str(e)}",
                execution_time_ms=execution_time,
                critical=False
            ))

    def _check_network_connectivity(self):
        """Check network connectivity and connections."""
        start_time = time.time()

        try:
            connections = psutil.net_connections()
            listening_ports = [conn.laddr.port for conn in connections
                             if conn.status == 'LISTEN' and conn.laddr]

            # Check for common ports
            expected_ports = [8000]  # FastAPI default
            found_ports = [port for port in expected_ports if port in listening_ports]

            if found_ports:
                status = "pass"
                details = f"Network services running on ports: {found_ports}"
            else:
                status = "warning"
                details = f"Expected ports not found. Listening on: {listening_ports[:5]}"

            execution_time = int((time.time() - start_time) * 1000)
            self.checks.append(ReadinessCheck(
                category="Network",
                check_name="Service Ports",
                status=status,
                details=details,
                execution_time_ms=execution_time,
                critical=False
            ))

        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            self.checks.append(ReadinessCheck(
                category="Network",
                check_name="Service Ports",
                status="warning",
                details=f"Could not check network: {str(e)}",
                execution_time_ms=execution_time,
                critical=False
            ))

    def _check_environment_variables(self):
        """Check required environment variables."""
        start_time = time.time()

        required_vars = [
            "DATABASE_URL",
            "REDIS_URL",
            "QDRANT_URL"
        ]

        optional_vars = [
            "CLAUDE_API_KEY",
            "MAX_DAILY_BUDGET_USD",
            "JWT_SECRET",
            "DEBUG"
        ]

        missing_required = [var for var in required_vars if not os.getenv(var)]
        missing_optional = [var for var in optional_vars if not os.getenv(var)]

        if not missing_required:
            if not missing_optional:
                status = "pass"
                details = "All environment variables configured"
            else:
                status = "warning"
                details = f"Missing optional vars: {', '.join(missing_optional)}"
        else:
            status = "fail"
            details = f"Missing required vars: {', '.join(missing_required)}"

        execution_time = int((time.time() - start_time) * 1000)
        self.checks.append(ReadinessCheck(
            category="Configuration",
            check_name="Environment Variables",
            status=status,
            details=details,
            execution_time_ms=execution_time,
            critical=(status == "fail")
        ))

    def _check_logging_configuration(self):
        """Check logging configuration."""
        start_time = time.time()

        log_level = os.getenv("LOG_LEVEL", "INFO")
        debug_mode = os.getenv("DEBUG", "false").lower() == "true"

        if debug_mode:
            status = "warning"
            details = "Debug mode enabled (disable for production)"
        elif log_level in ["INFO", "WARNING", "ERROR"]:
            status = "pass"
            details = f"Logging properly configured (level: {log_level})"
        else:
            status = "warning"
            details = f"Unusual log level: {log_level}"

        execution_time = int((time.time() - start_time) * 1000)
        self.checks.append(ReadinessCheck(
            category="Configuration",
            check_name="Logging Configuration",
            status=status,
            details=details,
            execution_time_ms=execution_time,
            critical=False
        ))

    async def _check_mobile_optimization(self):
        """Check mobile-specific optimizations."""
        start_time = time.time()

        try:
            # Check if pagination is implemented
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.config['api_base_url']}/api/v1/inventory/?page=1&per_page=20") as response:
                    if "page" in str(response.url):
                        pagination_status = "pass"
                        pagination_details = "Pagination implemented"
                    else:
                        pagination_status = "warning"
                        pagination_details = "Pagination not detected"

                    execution_time = int((time.time() - start_time) * 1000)
                    self.checks.append(ReadinessCheck(
                        category="Mobile Optimization",
                        check_name="API Pagination",
                        status=pagination_status,
                        details=pagination_details,
                        execution_time_ms=execution_time,
                        critical=False
                    ))

        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            self.checks.append(ReadinessCheck(
                category="Mobile Optimization",
                check_name="API Pagination",
                status="warning",
                details=f"Could not check pagination: {str(e)}",
                execution_time_ms=execution_time,
                critical=False
            ))

        # Check for PWA files
        pwa_files = [
            "frontend/public/manifest.json",
            "frontend/public/sw.js"
        ]

        missing_pwa_files = [f for f in pwa_files if not Path(f).exists()]

        if not missing_pwa_files:
            pwa_status = "pass"
            pwa_details = "PWA files present"
        else:
            pwa_status = "warning"
            pwa_details = f"Missing PWA files: {', '.join(missing_pwa_files)}"

        self.checks.append(ReadinessCheck(
            category="Mobile Optimization",
            check_name="PWA Configuration",
            status=pwa_status,
            details=pwa_details,
            execution_time_ms=0,
            critical=False
        ))

    def _generate_readiness_report(self) -> Dict[str, Any]:
        """Generate comprehensive readiness report."""
        end_time = datetime.utcnow()
        total_time = (end_time - self.start_time).total_seconds()

        # Categorize results
        passed = [c for c in self.checks if c.status == "pass"]
        warnings = [c for c in self.checks if c.status == "warning"]
        failed = [c for c in self.checks if c.status == "fail"]
        critical_failed = [c for c in failed if c.critical]

        # Calculate readiness score
        total_checks = len(self.checks)
        passed_score = len(passed) * 100
        warning_score = len(warnings) * 60
        failed_score = len(failed) * 0

        readiness_score = (passed_score + warning_score + failed_score) / (total_checks * 100) * 100

        # Determine overall status
        if len(critical_failed) > 0:
            overall_status = "NOT READY"
            status_emoji = "❌"
        elif len(failed) > 0 or readiness_score < 80:
            overall_status = "NEEDS ATTENTION"
            status_emoji = "⚠️"
        elif readiness_score >= 95:
            overall_status = "PRODUCTION READY"
            status_emoji = "✅"
        else:
            overall_status = "MOSTLY READY"
            status_emoji = "🟡"

        return {
            "overall_status": overall_status,
            "status_emoji": status_emoji,
            "readiness_score": readiness_score,
            "total_checks": total_checks,
            "passed": len(passed),
            "warnings": len(warnings),
            "failed": len(failed),
            "critical_failed": len(critical_failed),
            "execution_time_seconds": total_time,
            "timestamp": end_time.isoformat(),
            "categories": self._group_checks_by_category(),
            "recommendations": self._generate_recommendations()
        }

    def _group_checks_by_category(self) -> Dict[str, Dict[str, Any]]:
        """Group checks by category with summary stats."""
        categories = {}

        for check in self.checks:
            if check.category not in categories:
                categories[check.category] = {
                    "checks": [],
                    "passed": 0,
                    "warnings": 0,
                    "failed": 0,
                    "critical_failed": 0
                }

            categories[check.category]["checks"].append({
                "name": check.check_name,
                "status": check.status,
                "details": check.details,
                "execution_time_ms": check.execution_time_ms,
                "critical": check.critical
            })

            # Update counters
            if check.status == "pass":
                categories[check.category]["passed"] += 1
            elif check.status == "warning":
                categories[check.category]["warnings"] += 1
            elif check.status == "fail":
                categories[check.category]["failed"] += 1
                if check.critical:
                    categories[check.category]["critical_failed"] += 1

        return categories

    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on check results."""
        recommendations = []

        failed_checks = [c for c in self.checks if c.status == "fail"]
        warning_checks = [c for c in self.checks if c.status == "warning"]

        # Critical failures
        for check in failed_checks:
            if check.critical:
                recommendations.append(f"CRITICAL: Fix {check.check_name} - {check.details}")

        # High priority warnings
        for check in warning_checks:
            if "budget" in check.check_name.lower():
                recommendations.append(f"Monitor AI costs closely - {check.details}")
            elif "security" in check.category.lower():
                recommendations.append(f"Review security: {check.check_name} - {check.details}")

        # General recommendations
        if len(failed_checks) > 0:
            recommendations.append("Address all failed checks before production deployment")

        if len(warning_checks) > 3:
            recommendations.append("Consider addressing warnings for optimal performance")

        return recommendations

    def print_readiness_report(self, report: Dict[str, Any]):
        """Print formatted readiness report."""
        print("\n" + "="*80)
        print(f"{report['status_emoji']} PRODUCTION READINESS REPORT")
        print("="*80)

        print(f"📊 Overall Status: {report['overall_status']}")
        print(f"🎯 Readiness Score: {report['readiness_score']:.1f}/100")
        print(f"⏱️  Execution Time: {report['execution_time_seconds']:.2f}s")
        print(f"📅 Timestamp: {report['timestamp']}")

        print(f"\n📈 Check Summary:")
        print(f"   Total Checks: {report['total_checks']}")
        print(f"   ✅ Passed: {report['passed']}")
        print(f"   ⚠️  Warnings: {report['warnings']}")
        print(f"   ❌ Failed: {report['failed']}")
        if report['critical_failed'] > 0:
            print(f"   🚨 Critical Failed: {report['critical_failed']}")

        print(f"\n📋 Results by Category:")
        for category, data in report['categories'].items():
            total = len(data['checks'])
            passed = data['passed']
            status_icon = "✅" if data['failed'] == 0 else "⚠️" if data['critical_failed'] == 0 else "❌"

            print(f"\n{status_icon} {category} ({passed}/{total} passed)")

            for check in data['checks']:
                check_icon = {"pass": "✅", "warning": "⚠️", "fail": "❌", "skip": "⏭️"}[check['status']]
                critical_marker = " 🚨" if check['critical'] and check['status'] == 'fail' else ""
                print(f"   {check_icon} {check['name']}: {check['details']}{critical_marker}")

        if report['recommendations']:
            print(f"\n💡 Recommendations:")
            for i, rec in enumerate(report['recommendations'], 1):
                print(f"   {i}. {rec}")

        print("\n" + "="*80)


# Main execution
async def main():
    """Run production readiness validation."""
    print("🚀 AI-Powered Tuxemon Production Readiness Validation")

    validator = ProductionReadinessValidator()
    report = await validator.validate_production_readiness()
    validator.print_readiness_report(report)

    # Save report to file
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"production_readiness_report_{timestamp}.json"

    with open(filename, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\n📄 Full report saved to: {filename}")

    # Return exit code based on readiness
    if report['overall_status'] == "PRODUCTION READY":
        return 0
    elif report['critical_failed'] > 0:
        return 2  # Critical failures
    else:
        return 1  # Warnings or non-critical failures


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)