#!/usr/bin/env python3
"""
Production Testing Suite Runner for AI-Powered Tuxemon
Windows-compatible version without Unicode issues
"""

import asyncio
import json
import time
from datetime import datetime

# Import our production testing modules
from production_readiness.readiness_validator import ProductionReadinessValidator
from load_testing.load_test_runner import LoadTestRunner, LoadTestConfig
from load_testing.mobile_performance_test import MobilePerformanceTester


async def run_production_readiness():
    """Run production readiness validation."""
    print("=" * 60)
    print("PRODUCTION READINESS VALIDATION")
    print("=" * 60)

    validator = ProductionReadinessValidator()
    report = await validator.validate_production_readiness()

    # Print simplified report without emojis
    print(f"\nOverall Status: {report['overall_status']}")
    print(f"Readiness Score: {report['readiness_score']:.1f}/100")
    print(f"Execution Time: {report['execution_time_seconds']:.2f}s")

    print(f"\nCheck Summary:")
    print(f"  Total Checks: {report['total_checks']}")
    print(f"  Passed: {report['passed']}")
    print(f"  Warnings: {report['warnings']}")
    print(f"  Failed: {report['failed']}")
    if report['critical_failed'] > 0:
        print(f"  Critical Failed: {report['critical_failed']}")

    print(f"\nResults by Category:")
    for category, data in report['categories'].items():
        total = len(data['checks'])
        passed = data['passed']
        status_symbol = "PASS" if data['failed'] == 0 else "WARN" if data['critical_failed'] == 0 else "FAIL"

        print(f"\n{status_symbol} {category} ({passed}/{total} passed)")

        for check in data['checks']:
            check_symbol = {"pass": "PASS", "warning": "WARN", "fail": "FAIL", "skip": "SKIP"}[check['status']]
            critical_marker = " CRITICAL" if check['critical'] and check['status'] == 'fail' else ""
            print(f"  {check_symbol} {check['name']}: {check['details']}{critical_marker}")

    if report['recommendations']:
        print(f"\nRecommendations:")
        for i, rec in enumerate(report['recommendations'], 1):
            print(f"  {i}. {rec}")

    # Save report
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"production_readiness_report_{timestamp}.json"
    with open(filename, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\nFull report saved to: {filename}")
    return report


async def run_load_testing():
    """Run load testing suite."""
    print("\n" + "=" * 60)
    print("LOAD TESTING SUITE")
    print("=" * 60)

    # Run a standard load test
    config = LoadTestConfig(
        concurrent_users=25,  # Reduced for compatibility
        test_duration_seconds=120,  # 2 minutes
        ramp_up_seconds=20
    )

    print(f"Starting load test with {config.concurrent_users} concurrent users")
    print(f"Duration: {config.test_duration_seconds}s")
    print(f"Target: {config.base_url}")

    runner = LoadTestRunner(config)
    results = await runner.run()

    print(f"\nLoad Test Results:")
    print(f"  Total Requests: {results.total_requests:,}")
    print(f"  Success Rate: {results.success_rate:.2f}%")
    print(f"  Requests/Second: {results.requests_per_second:.2f}")
    print(f"  Average Response Time: {results.avg_response_time_ms:.0f}ms")
    print(f"  P95 Response Time: {results.p95_response_time_ms:.0f}ms")
    print(f"  P99 Response Time: {results.p99_response_time_ms:.0f}ms")
    print(f"  Max Response Time: {results.max_response_time_ms:.0f}ms")

    if results.errors_by_endpoint:
        print(f"\nErrors by Endpoint:")
        for endpoint, count in sorted(results.errors_by_endpoint.items(), key=lambda x: x[1], reverse=True):
            print(f"  {endpoint}: {count} errors")

    print(f"\nCost Analysis:")
    cost = results.cost_analysis
    print(f"  Estimated Test Cost: ${cost['estimated_total_cost']:.4f}")
    print(f"  Claude API Calls: {cost['estimated_claude_calls']:.0f}")
    print(f"  Local LLM Calls: {cost['estimated_local_calls']:.0f}")
    print(f"  Projected Daily Cost: ${cost['projected_daily_cost']:.2f}")
    print(f"  Projected Monthly Cost: ${cost['projected_monthly_cost']:.2f}")

    # Performance assessment
    print(f"\nPerformance Assessment:")
    if results.success_rate >= 99.5:
        print("  SUCCESS RATE: Excellent (>=99.5%)")
    elif results.success_rate >= 95:
        print("  SUCCESS RATE: Good (>=95%)")
    else:
        print("  SUCCESS RATE: Poor (<95%)")

    if results.p95_response_time_ms <= 500:
        print("  RESPONSE TIME: Excellent P95 <=500ms")
    elif results.p95_response_time_ms <= 1000:
        print("  RESPONSE TIME: Acceptable P95 <=1000ms")
    else:
        print("  RESPONSE TIME: Poor P95 >1000ms")

    if results.requests_per_second >= 50:
        print("  THROUGHPUT: Good (>=50 RPS)")
    elif results.requests_per_second >= 25:
        print("  THROUGHPUT: Acceptable (>=25 RPS)")
    else:
        print("  THROUGHPUT: Poor (<25 RPS)")

    # Save results
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"load_test_results_{timestamp}.json"

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

    print(f"\nLoad test results saved to: {filename}")
    return results


async def run_mobile_performance():
    """Run mobile performance testing."""
    print("\n" + "=" * 60)
    print("MOBILE PERFORMANCE TESTING")
    print("=" * 60)

    tester = MobilePerformanceTester()
    results = await tester.run_full_mobile_test_suite()

    total_scenarios = len(results)
    excellent_ux = sum(1 for r in results.values() if r.user_experience_score >= 90)
    good_ux = sum(1 for r in results.values() if 70 <= r.user_experience_score < 90)
    poor_ux = sum(1 for r in results.values() if r.user_experience_score < 70)

    print(f"\nMobile Test Summary:")
    print(f"  Total Scenarios: {total_scenarios}")
    print(f"  Excellent UX: {excellent_ux} ({excellent_ux/total_scenarios*100:.1f}%)")
    print(f"  Good UX: {good_ux} ({good_ux/total_scenarios*100:.1f}%)")
    print(f"  Poor UX: {poor_ux} ({poor_ux/total_scenarios*100:.1f}%)")

    print(f"\nDetailed Results:")

    for scenario_name, result in results.items():
        status = "PASS" if result.user_experience_score >= 80 else "WARN" if result.user_experience_score >= 60 else "FAIL"

        print(f"\n{status} {scenario_name.upper().replace('_', ' ')}")
        print(f"  Total Time: {result.total_time_ms}ms")
        print(f"  UX Score: {result.user_experience_score:.1f}/100")
        print(f"  Battery Score: {result.battery_efficiency_score:.1f} (lower better)")
        print(f"  API Calls: {result.api_calls_count}")
        print(f"  Data Transfer: {result.total_data_transferred_kb:.2f}KB")
        print(f"  Largest Response: {result.largest_response_kb:.2f}KB")

        if result.performance_bottlenecks:
            print(f"  Bottlenecks:")
            for bottleneck in result.performance_bottlenecks:
                print(f"    - {bottleneck}")

    # Overall assessment
    print(f"\nMobile Readiness Assessment:")

    avg_ux_score = sum(r.user_experience_score for r in results.values()) / len(results)
    avg_battery_score = sum(r.battery_efficiency_score for r in results.values()) / len(results)
    max_response_time = max(r.total_time_ms for r in results.values())
    total_data_usage = sum(r.total_data_transferred_kb for r in results.values())

    if avg_ux_score >= 85:
        print("  USER EXPERIENCE: Excellent")
    elif avg_ux_score >= 70:
        print("  USER EXPERIENCE: Good")
    else:
        print("  USER EXPERIENCE: Needs Improvement")

    if avg_battery_score <= 50:
        print("  BATTERY EFFICIENCY: Excellent")
    elif avg_battery_score <= 80:
        print("  BATTERY EFFICIENCY: Good")
    else:
        print("  BATTERY EFFICIENCY: Poor")

    if max_response_time <= 2000:
        print("  RESPONSIVENESS: Excellent")
    elif max_response_time <= 3000:
        print("  RESPONSIVENESS: Acceptable")
    else:
        print("  RESPONSIVENESS: Too Slow")

    if total_data_usage <= 200:
        print("  DATA USAGE: Efficient")
    elif total_data_usage <= 500:
        print("  DATA USAGE: Moderate")
    else:
        print("  DATA USAGE: Excessive")

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

    print(f"\nMobile test results saved to: {filename}")
    return results


async def main():
    """Run complete production testing suite."""
    start_time = time.time()

    print("AI-POWERED TUXEMON PRODUCTION TESTING SUITE")
    print("=" * 60)

    try:
        # Run production readiness validation
        readiness_report = await run_production_readiness()

        # Run load testing
        load_results = await run_load_testing()

        # Run mobile performance testing
        mobile_results = await run_mobile_performance()

        # Generate summary report
        total_time = time.time() - start_time

        print("\n" + "=" * 60)
        print("PRODUCTION TESTING SUMMARY")
        print("=" * 60)

        print(f"Total Execution Time: {total_time:.2f}s")

        # Readiness summary
        print(f"\nPRODUCTION READINESS:")
        print(f"  Overall Status: {readiness_report['overall_status']}")
        print(f"  Score: {readiness_report['readiness_score']:.1f}/100")
        print(f"  Critical Issues: {readiness_report['critical_failed']}")

        # Load testing summary
        print(f"\nLOAD TESTING:")
        print(f"  Success Rate: {load_results.success_rate:.1f}%")
        print(f"  P95 Response Time: {load_results.p95_response_time_ms:.0f}ms")
        print(f"  Throughput: {load_results.requests_per_second:.1f} RPS")

        # Mobile testing summary
        avg_ux = sum(r.user_experience_score for r in mobile_results.values()) / len(mobile_results)
        print(f"\nMOBILE PERFORMANCE:")
        print(f"  Average UX Score: {avg_ux:.1f}/100")
        print(f"  Scenarios Tested: {len(mobile_results)}")

        # Final assessment
        overall_ready = (
            readiness_report['overall_status'] in ["PRODUCTION READY", "MOSTLY READY"] and
            load_results.success_rate >= 95 and
            load_results.p95_response_time_ms <= 1000 and
            avg_ux >= 70
        )

        print(f"\nFINAL ASSESSMENT: {'SYSTEM READY FOR PRODUCTION' if overall_ready else 'SYSTEM NEEDS ATTENTION BEFORE PRODUCTION'}")

    except Exception as e:
        print(f"\nERROR: Production testing failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)