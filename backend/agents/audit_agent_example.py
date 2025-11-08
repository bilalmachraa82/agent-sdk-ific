"""
AuditAgent Usage Examples
Demonstrates comprehensive logging, cost tracking, and audit report generation.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from .audit_agent import (
    AuditAgent,
    AgentType,
    OperationStatus,
    ResourceType,
)


async def example_basic_logging(db: AsyncSession, tenant_id, user_id):
    """Example: Basic operation logging."""
    audit_agent = AuditAgent(db=db)

    # Log a file upload operation
    log = await audit_agent.log_operation(
        action="upload_saft_file",
        resource_type=ResourceType.FILE_UPLOAD.value,
        resource_id=uuid4(),
        tenant_id=tenant_id,
        user_id=user_id,
        agent_name=AgentType.INPUT_AGENT.value,
        metadata={
            "file_name": "company_saft_2023.xml",
            "file_size_bytes": 2500000,
            "file_type": "SAF-T",
        },
    )

    print(f"Created audit log: {log.id}")
    print(f"Action: {log.action}")
    print(f"Status: {log.status}")


async def example_logging_with_cost_tracking(db: AsyncSession, tenant_id, project_id):
    """Example: Log operation with cost tracking."""
    audit_agent = AuditAgent(db=db)

    # Log narrative generation with token usage
    log = await audit_agent.log_operation(
        action="generate_project_narrative",
        resource_type=ResourceType.NARRATIVE_GENERATION.value,
        resource_id=uuid4(),
        tenant_id=tenant_id,
        project_id=project_id,
        agent_name=AgentType.NARRATIVE_AGENT.value,
        tokens_used=15000,  # Claude consumed 15k tokens
        # Cost will be auto-calculated
        metadata={
            "model": "claude-3-5-sonnet-20241022",
            "narrative_type": "project_description",
            "word_count": 850,
        },
    )

    print(f"Tokens used: {log.tokens_used}")
    print(f"Cost: €{log.cost_euros}")


async def example_logging_with_data_hashing(db: AsyncSession, tenant_id, project_id):
    """Example: Log operation with input/output data hashing."""
    audit_agent = AuditAgent(db=db)

    # Financial calculation with data hashing for audit trail
    input_data = {
        "total_investment": 500000,
        "eligible_investment": 450000,
        "funding_requested": 225000,
        "project_duration_years": 5,
    }

    output_data = {
        "valf": -45000,
        "trf": 3.2,
        "payback_period": 4.5,
        "roi": 15.8,
    }

    log = await audit_agent.log_operation(
        action="calculate_financial_model",
        resource_type=ResourceType.FINANCIAL_MODEL.value,
        resource_id=uuid4(),
        tenant_id=tenant_id,
        project_id=project_id,
        agent_name=AgentType.FINANCIAL_AGENT.value,
        input_data=input_data,
        output_data=output_data,
        metadata={
            "model_version": "1.0.0",
            "calculation_method": "deterministic",
            "discount_rate": 0.04,
        },
    )

    print(f"Input hash: {log.input_hash}")
    print(f"Output hash: {log.output_hash}")
    print("Data integrity can be verified by recomputing hashes")


async def example_logging_error_operation(db: AsyncSession, tenant_id, user_id):
    """Example: Log a failed operation."""
    audit_agent = AuditAgent(db=db)

    try:
        # Simulate an error
        raise ValueError("Invalid SAF-T file format")
    except Exception as e:
        import traceback

        log = await audit_agent.log_operation(
            action="parse_saft_file",
            resource_type=ResourceType.FILE_UPLOAD.value,
            resource_id=uuid4(),
            tenant_id=tenant_id,
            user_id=user_id,
            agent_name=AgentType.INPUT_AGENT.value,
            status=OperationStatus.ERROR.value,
            error_message=str(e),
            error_stacktrace=traceback.format_exc(),
            metadata={
                "file_name": "invalid_file.xml",
            },
        )

        print(f"Error logged: {log.error_message}")


async def example_get_project_audit_trail(db: AsyncSession, tenant_id, project_id):
    """Example: Retrieve complete audit trail for a project."""
    audit_agent = AuditAgent(db=db)

    # Get all audit logs for this project
    logs = await audit_agent.get_project_audit_trail(
        project_id=project_id,
        tenant_id=tenant_id,
    )

    print(f"Found {len(logs)} audit log entries")

    for log in logs:
        print(f"- {log.created_at}: {log.action} by {log.agent_name} ({log.status})")


async def example_query_logs_by_criteria(db: AsyncSession, tenant_id):
    """Example: Query audit logs with filters."""
    audit_agent = AuditAgent(db=db)

    # Get all error logs from last 7 days
    logs = await audit_agent.get_logs_by_criteria(
        tenant_id=tenant_id,
        start_date=datetime.utcnow() - timedelta(days=7),
        end_date=datetime.utcnow(),
        status=OperationStatus.ERROR.value,
    )

    print(f"Errors in last 7 days: {len(logs)}")

    # Get all operations by NarrativeAgent
    narrative_logs = await audit_agent.get_logs_by_criteria(
        tenant_id=tenant_id,
        agent_name=AgentType.NARRATIVE_AGENT.value,
        limit=50,
    )

    print(f"NarrativeAgent operations: {len(narrative_logs)}")

    # Get all file upload operations
    upload_logs = await audit_agent.get_logs_by_criteria(
        tenant_id=tenant_id,
        action="upload_saft_file",
        resource_type=ResourceType.FILE_UPLOAD.value,
    )

    print(f"File uploads: {len(upload_logs)}")


async def example_calculate_project_cost(db: AsyncSession, tenant_id, project_id):
    """Example: Calculate comprehensive cost breakdown for a project."""
    audit_agent = AuditAgent(db=db)

    cost = await audit_agent.calculate_project_cost(
        project_id=project_id,
        tenant_id=tenant_id,
    )

    print(f"Project: {cost.project_name}")
    print(f"Total operations: {cost.operation_count}")
    print(f"  - Successful: {cost.successful_operations}")
    print(f"  - Failed: {cost.failed_operations}")
    print()
    print(f"Total tokens used: {cost.total_tokens_used:,}")
    print(f"Total API cost: €{cost.total_api_cost_euros}")
    print(f"Estimated storage cost: €{cost.estimated_storage_cost_euros}")
    print(f"Total cost: €{cost.total_cost_euros}")
    print()
    print("Cost by agent:")
    for agent, agent_cost in cost.agent_costs.items():
        tokens = cost.agent_tokens.get(agent, 0)
        print(f"  - {agent}: €{agent_cost} ({tokens:,} tokens)")
    print()
    print(f"Average operation time: {cost.average_operation_time_ms:.2f}ms")
    print(f"Total processing time: {cost.total_processing_time_ms:,}ms")


async def example_generate_audit_report(db: AsyncSession, tenant_id):
    """Example: Generate comprehensive audit report for a tenant."""
    audit_agent = AuditAgent(db=db)

    # Generate monthly report
    start_date = datetime.utcnow() - timedelta(days=30)
    end_date = datetime.utcnow()

    report = await audit_agent.generate_audit_report(
        tenant_id=tenant_id,
        start_date=start_date,
        end_date=end_date,
    )

    print("=== AUDIT REPORT ===")
    print(f"Period: {report.start_date.date()} to {report.end_date.date()}")
    print()
    print("Overview:")
    print(f"  Total operations: {report.total_operations}")
    print(f"  Total projects: {report.total_projects}")
    print(f"  Total users: {report.total_users}")
    print()
    print("Costs:")
    print(f"  API cost: €{report.total_api_cost_euros}")
    print(f"  Storage cost: €{report.total_storage_cost_euros}")
    print(f"  Total cost: €{report.total_cost_euros}")
    print(f"  Total tokens: {report.total_tokens_used:,}")
    print()
    print("Operations by action:")
    for action, count in sorted(
        report.operations_by_action.items(), key=lambda x: x[1], reverse=True
    ):
        print(f"  - {action}: {count}")
    print()
    print("Operations by agent:")
    for agent, count in sorted(
        report.operations_by_agent.items(), key=lambda x: x[1], reverse=True
    ):
        print(f"  - {agent}: {count}")
    print()
    print("Cost by agent:")
    for agent, agent_cost in sorted(
        report.cost_by_agent.items(), key=lambda x: x[1], reverse=True
    ):
        print(f"  - {agent}: €{agent_cost}")
    print()
    print("Performance:")
    print(f"  Average operation time: {report.average_operation_time_ms:.2f}ms")
    print(f"  P95 operation time: {report.p95_operation_time_ms:.2f}ms")
    print(f"  P99 operation time: {report.p99_operation_time_ms:.2f}ms")
    print()
    print("Errors:")
    print(f"  Total errors: {report.total_errors}")
    if report.errors_by_type:
        print("  Error breakdown:")
        for error_type, count in sorted(
            report.errors_by_type.items(), key=lambda x: x[1], reverse=True
        ):
            print(f"    - {error_type}: {count}")
    print()
    print("Compliance:")
    print(f"  Operations with audit trail: {report.operations_with_audit_trail}")
    print(f"  Compliance percentage: {report.compliance_percentage}%")


async def example_check_daily_cost_limit(db: AsyncSession, tenant_id):
    """Example: Check daily cost and limits."""
    audit_agent = AuditAgent(db=db)

    summary = await audit_agent.get_daily_cost_summary(
        tenant_id=tenant_id,
    )

    print(f"Daily cost summary for {summary['date']}:")
    print(f"  Total cost: €{summary['total_cost_euros']:.4f}")
    print(f"  Total tokens: {summary['total_tokens']:,}")
    print(f"  Operations: {summary['operation_count']}")
    print(f"  Daily limit: €{summary['daily_limit_euros']:.2f}")
    print(f"  Limit usage: {summary['limit_percentage']:.1f}%")

    if summary["limit_exceeded"]:
        print("  ⚠️  WARNING: Daily limit exceeded!")
    else:
        remaining = summary["daily_limit_euros"] - summary["total_cost_euros"]
        print(f"  ✓ Remaining: €{remaining:.2f}")


async def example_complete_evf_workflow_audit(
    db: AsyncSession, tenant_id, user_id, project_id
):
    """
    Example: Complete EVF processing workflow with comprehensive auditing.
    This demonstrates how audit logs are created throughout the entire process.
    """
    audit_agent = AuditAgent(db=db)

    print("=== EVF Processing with Audit Trail ===\n")

    # 1. File Upload
    print("1. Uploading SAF-T file...")
    await audit_agent.log_operation(
        action="upload_saft_file",
        resource_type=ResourceType.FILE_UPLOAD.value,
        resource_id=uuid4(),
        tenant_id=tenant_id,
        user_id=user_id,
        project_id=project_id,
        agent_name=AgentType.INPUT_AGENT.value,
        input_data=b"<SAF-T>... file content ...</SAF-T>",
        request_duration_ms=2500,
    )

    # 2. Parse and validate SAF-T
    print("2. Parsing SAF-T file...")
    await audit_agent.log_operation(
        action="parse_saft",
        resource_type=ResourceType.FILE_UPLOAD.value,
        resource_id=uuid4(),
        tenant_id=tenant_id,
        project_id=project_id,
        agent_name=AgentType.INPUT_AGENT.value,
        input_data={"file_hash": "abc123..."},
        output_data={"companies": 1, "transactions": 5000, "total_revenue": 2500000},
        request_duration_ms=8500,
    )

    # 3. Compliance check
    print("3. Checking PT2030 compliance...")
    await audit_agent.log_operation(
        action="check_pt2030_compliance",
        resource_type=ResourceType.COMPLIANCE_CHECK.value,
        resource_id=uuid4(),
        tenant_id=tenant_id,
        project_id=project_id,
        agent_name=AgentType.COMPLIANCE_AGENT.value,
        output_data={"compliant": True, "rules_checked": 25, "warnings": []},
        request_duration_ms=1200,
    )

    # 4. Financial model calculation
    print("4. Calculating financial model...")
    await audit_agent.log_operation(
        action="calculate_financial_model",
        resource_type=ResourceType.FINANCIAL_MODEL.value,
        resource_id=uuid4(),
        tenant_id=tenant_id,
        project_id=project_id,
        agent_name=AgentType.FINANCIAL_AGENT.value,
        input_data={
            "total_investment": 500000,
            "cash_flows": [100000, 120000, 140000, 150000, 160000],
        },
        output_data={"valf": -42000, "trf": 3.5, "payback_period": 4.2},
        request_duration_ms=450,
    )

    # 5. Generate narrative (uses Claude API)
    print("5. Generating project narrative...")
    await audit_agent.log_operation(
        action="generate_narrative",
        resource_type=ResourceType.NARRATIVE_GENERATION.value,
        resource_id=uuid4(),
        tenant_id=tenant_id,
        project_id=project_id,
        agent_name=AgentType.NARRATIVE_AGENT.value,
        tokens_used=12500,  # Claude tokens
        output_data={"word_count": 750, "sections": 5},
        request_duration_ms=4200,
    )

    # 6. Generate Excel report
    print("6. Generating Excel report...")
    await audit_agent.log_operation(
        action="generate_excel_report",
        resource_type=ResourceType.EVF_PROJECT.value,
        resource_id=project_id,
        tenant_id=tenant_id,
        project_id=project_id,
        agent_name="report_generator",
        output_data={"file_size_bytes": 125000, "sheets": 8},
        request_duration_ms=1800,
    )

    # 7. Finalize and approve
    print("7. Finalizing project...")
    await audit_agent.log_operation(
        action="approve_project",
        resource_type=ResourceType.EVF_PROJECT.value,
        resource_id=project_id,
        tenant_id=tenant_id,
        user_id=user_id,
        project_id=project_id,
        agent_name=AgentType.AUDIT_AGENT.value,
        request_duration_ms=150,
    )

    print("\n=== Processing Complete ===")

    # Calculate final cost
    cost = await audit_agent.calculate_project_cost(
        project_id=project_id,
        tenant_id=tenant_id,
    )

    print(f"\nTotal cost: €{cost.total_cost_euros}")
    print(f"Total time: {cost.total_processing_time_ms / 1000:.2f}s")
    print(f"Operations: {cost.operation_count}")


# ============================================================================
# FastAPI Integration Example
# ============================================================================


async def example_fastapi_middleware_integration():
    """
    Example: Integrate AuditAgent into FastAPI middleware.
    This shows how to automatically log all API requests.
    """

    # This would be in your FastAPI app
    from fastapi import FastAPI, Request
    from time import time

    app = FastAPI()

    @app.middleware("http")
    async def audit_middleware(request: Request, call_next):
        """Middleware to automatically log all API requests."""
        start_time = time()

        # Get tenant and user from request (from JWT or headers)
        tenant_id = request.state.tenant_id  # Set by auth middleware
        user_id = request.state.user_id  # Set by auth middleware

        try:
            response = await call_next(request)
            duration_ms = int((time() - start_time) * 1000)

            # Log successful request
            audit_agent = AuditAgent(db=request.state.db)
            await audit_agent.log_operation(
                action=f"{request.method}_{request.url.path}",
                resource_type="api_request",
                resource_id=None,
                tenant_id=tenant_id,
                user_id=user_id,
                request_method=request.method,
                request_path=str(request.url.path),
                request_duration_ms=duration_ms,
                ip_address=request.client.host,
                user_agent=request.headers.get("user-agent"),
                status=OperationStatus.SUCCESS.value,
                metadata={
                    "status_code": response.status_code,
                },
            )

            return response

        except Exception as e:
            duration_ms = int((time() - start_time) * 1000)

            # Log failed request
            audit_agent = AuditAgent(db=request.state.db)
            await audit_agent.log_operation(
                action=f"{request.method}_{request.url.path}",
                resource_type="api_request",
                resource_id=None,
                tenant_id=tenant_id,
                user_id=user_id,
                request_method=request.method,
                request_path=str(request.url.path),
                request_duration_ms=duration_ms,
                ip_address=request.client.host,
                user_agent=request.headers.get("user-agent"),
                status=OperationStatus.ERROR.value,
                error_message=str(e),
            )

            raise


# ============================================================================
# Compliance Report Example (10-year retention)
# ============================================================================


async def example_compliance_report_for_regulator(db: AsyncSession, tenant_id):
    """
    Example: Generate compliance report for regulatory audit.
    PT2030 requires 10-year retention of all financial calculations.
    """
    audit_agent = AuditAgent(db=db)

    # Generate report for entire history
    report = await audit_agent.generate_audit_report(
        tenant_id=tenant_id,
        start_date=datetime(2024, 1, 1),  # Beginning of time
        end_date=datetime.utcnow(),
    )

    print("=== COMPLIANCE REPORT FOR REGULATORY AUDIT ===\n")
    print(f"Tenant: {tenant_id}")
    print(f"Report generated: {report.generated_at}")
    print(f"Period: {report.start_date} to {report.end_date}")
    print()
    print("AUDIT TRAIL COMPLETENESS")
    print(f"  Total operations: {report.total_operations}")
    print(f"  Operations with complete audit trail: {report.operations_with_audit_trail}")
    print(f"  Compliance percentage: {report.compliance_percentage}%")
    print()
    print("OPERATION BREAKDOWN")
    print(f"  Total projects processed: {report.total_projects}")
    print(f"  Financial calculations: {report.operations_by_action.get('calculate_financial_model', 0)}")
    print(f"  Compliance checks: {report.operations_by_action.get('check_pt2030_compliance', 0)}")
    print()
    print("ERROR TRACKING")
    print(f"  Total errors: {report.total_errors}")
    print(f"  Error rate: {(report.total_errors / report.total_operations * 100):.2f}%")
    print()
    print("All operations are logged with SHA-256 hashes for data integrity.")
    print("Audit logs are immutable and stored for 10 years per PT2030 requirements.")
