# Agent Observability with OpenTelemetry

This project includes production-ready OpenTelemetry observability that provides consistent behavior across local development and deployed environments. The implementation automatically instruments LLM calls, HTTP requests, and application logs with minimal configuration while coexisting with ADK's internal telemetry infrastructure.

## What's Instrumented

- **LLM Operations**: Google Generative AI SDK calls with request/response details
- **HTTP Requests**: External API calls with timing and status information
- **Structured Logging**: JSON logs with automatic trace correlation for Google Cloud Logging
- **Tool Invocations**: Agent tool calls include invocation context for debugging

## Key Features

- **Consistent Custom Setup**: Single `setup_opentelemetry()` function used across all environments (local and deployed)
- **Process-Level Tracking**: Custom resource configuration with `SERVICE_INSTANCE_ID` based on process ID
- **Google Cloud Integration**: Direct export to Google Cloud Trace (OTLP) and Cloud Logging
- **Trace Correlation**: Logs automatically include trace context via `LoggingInstrumentor`
- **Service Identification**: OpenTelemetry `service.name` set to `AGENT_NAME` environment variable
- **Authentication**: Uses Application Default Credentials (ADC) for Google Cloud APIs

## Configuration

**📖 [Complete Environment Variables Reference](environment_variables.md)** - See the complete guide for all observability configuration options

**Key observability variables:**
- `AGENT_NAME`: OpenTelemetry service identifier (required)
- `LOG_LEVEL`: Logging verbosity (default: `INFO`)
- `GOOGLE_CLOUD_PROJECT`: Required for trace and log export
- `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT`: Capture LLM content (default: `true`)

## Usage

### Local Development
```bash
uv run local-agent
```
- Custom OpenTelemetry setup with Google Cloud export
- ADK web UI for interactive testing (with trace visualization)
- Identical observability configuration to deployed agents

### Production Deployment
```bash
uv run deploy
```
- Same custom OpenTelemetry setup as local development
- **Recommended**: Set `LOG_LEVEL=INFO` to minimize logging costs
- Full Cloud Trace and Cloud Logging integration

### Observability Behavior Across Environments
- **Consistent Setup**: Identical configuration for local and deployed agents
- **ADK Web UI**: Available only in local development (`uv run local-agent`)
- **Google Cloud Observability**: Available in all environments
- **Trace Correlation**: Logs include trace context for comprehensive debugging
- **Logs Location**: `logName="projects/{GOOGLE_CLOUD_PROJECT}/logs/{AGENT_NAME}-otel-logs"`

## Implementation

- `GoogleGenAiSdkInstrumentor`: Instruments Google Gen AI SDK operations
- `LoggingInstrumentor`: Adds trace context to log records
- `CloudLoggingExporter`: Direct export to Google Cloud Logging
- `OTLPSpanExporter`: Exports spans to Google Cloud Trace using the Telemetry API

## Resources

- [Vertex AI | Agent Engine | Trace an Agent](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/manage/tracing)
- [Google Cloud Observability | Instrument ADK Applications with OpenTelemetry](https://cloud.google.com/stackdriver/docs/instrumentation/ai-agent-adk)
- [Google Cloud Trace | View Generative AI Events](https://cloud.google.com/trace/docs/finding-traces#view_generative_ai_events)
- [OpenTelemetry | AI Agent Observability Best Practices](https://opentelemetry.io/blog/2025/ai-agent-observability/)
- [OpenTelemetry | Semantic Conventions for Generative AI](https://opentelemetry.io/docs/specs/semconv/gen-ai/)
- [OpenTelemetry Environment Variables](https://opentelemetry.io/docs/specs/otel/configuration/sdk-environment-variables/)

**[← Back to Documentation](../README.md#documentation)**
