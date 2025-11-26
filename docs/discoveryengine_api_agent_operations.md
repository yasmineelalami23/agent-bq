# Discovery Engine API agent operations
This document provides a set of `curl` commands to configure agents with the Discovery Engine API.

## Prerequisites

### Configure `gcloud` CLI (not required when using [Cloud Shell](https://cloud.google.com/shell/docs/launching-cloud-shell))
```sh
# Authenticate.
gcloud auth login

# Configure the default project.
gcloud config set project "your-project-id"

# Populate Application Default Credentials.
gcloud auth application-default login
```

### Set variables.
```sh
# Resource-specific
LOCATION="global"  # one of "global", "us", or "eu"
API_VERSION="v1alpha"  # one of "v1", "v1alpha", or "v1beta"
AGENTSPACE_APP_ID="your-agentspace-app-id_123456789012345"  # replace with your App/Engine ID

# Get the project number from the `gcloud` default project ID.
export PROJECT_NUMBER=$(gcloud projects describe $(gcloud config list --format='value(core.project)') --format='value(projectNumber)')

# Form the base discoveryengine API domain depending on the chosen location.
if [[ $LOCATION != "global" ]]; then
    API_BASE_DOMAIN="https://${LOCATION}-discoveryengine.googleapis.com"
else
    API_BASE_DOMAIN="https://discoveryengine.googleapis.com"
fi

COLLECTIONS="projects/${PROJECT_NUMBER}/locations/${LOCATION}/collections"
export COLLECTIONS_URL="${API_BASE_DOMAIN}/${API_VERSION}/${COLLECTIONS}"

ENGINE="${COLLECTIONS}/default_collection/engines/${AGENTSPACE_APP_ID}"
export ENGINE_URL="${API_BASE_DOMAIN}/${API_VERSION}/${ENGINE}"
```

## General engine and agent operations

### Get all collection details
Provides configuration details about all connected data stores.
```sh
curl -X GET -H "Authorization: Bearer $(gcloud auth print-access-token)" \
-H "Content-Type: application/json" \
-H "X-Goog-User-Project: ${PROJECT_NUMBER}" "${COLLECTIONS_URL}"
```

### Get engine details
```sh
curl -X GET -H "Authorization: Bearer $(gcloud auth print-access-token)" \
-H "Content-Type: application/json" \
-H "X-Goog-User-Project: ${PROJECT_NUMBER}" "${ENGINE_URL}"
```

### Get assistants
```sh
curl -X GET -H "Authorization: Bearer $(gcloud auth print-access-token)" \
-H "Content-Type: application/json" \
-H "X-Goog-User-Project: ${PROJECT_NUMBER}" "${ENGINE_URL}/assistants"
```

### Get agents registered with the default assistant
```sh
curl -X GET -H "Authorization: Bearer $(gcloud auth print-access-token)" \
-H "Content-Type: application/json" \
-H "X-Goog-User-Project: ${PROJECT_NUMBER}" "${ENGINE_URL}/assistants/default_assistant/agents"
```

## ADK agent operations

### Define registration parameters
- PROJECT_ID: the GCP project ID.
- REGION: the GCP region of the deployed agent engine (aka reasoning engine) resource. I.e., "us-central1".
- DISPLAY_NAME: the display name of the agent.
- DESCRIPTION: the description of the agent, displayed on the frontend; it is only for the user’s benefit.
- ICON_URI: The public URI of the icon to display near the name of the agent. Alternatively you can pass Base64-encoded image file contents, but in that case you have to use icon.content instead of icon.uri.
- TOOL_DESCRIPTION: the description / prompt of the agent used by the LLM to route requests to the agent. Must properly describe what the agent does. Never shown to the user.
- ADK_DEPLOYMENT_ID: the ID of the reasoning engine endpoint where the ADK agent is deployed.
- AUTH_ID: [OPTIONAL] the IDs of the authorization resources; can be omitted, can be one or can be more than one.

**NOTE**:
- The "authorizations" tag is optional; it is only needed if the Agent needs to act on behalf of the users (when it needs OAuth 2.0 support).
- To help to distinguish between DESCRIPTION and TOOL_DESCRIPTION see the following example: for an Invoice Scraper agent the description could be: “Extract key information from uploaded invoices for business travel”. The tool description prompt could be: “You are an expert invoice data extractor for business travel expenses. Your task is to extract key information from user-uploaded invoice documents.”

```sh
export PROJECT_ID="your-project-id"
export REGION="us-central1"  # replace with your region
export DISPLAY_NAME="Your agent's display name"
export DESCRIPTION="Do this thing this way."
export ICON_URI="https://example.com/my-image.png"
export TOOL_DESCRIPTION="You are an expert at doing a thing. Your task is to do the thing in a certain way."
export ADK_DEPLOYMENT_ID="123456789012345"
export AUTH_ID="098765432109876"  # optional: only set this if using OAuth
```

### Check for duplicate reasoning engine ID registrations
```sh
EXISTING_IDS=$(
    curl -X GET -H "Authorization: Bearer $(gcloud auth print-access-token)" \
    -H "Content-Type: application/json" \
    -H "X-Goog-User-Project: ${PROJECT_NUMBER}" "${ENGINE_URL}/assistants/default_assistant/agents" | \
    jq -r '.agents[]?.adkAgentDefinition.provisionedReasoningEngine.reasoningEngine | split("/") | last' 2>/dev/null
)

if echo "$EXISTING_IDS" | grep -q "^${ADK_DEPLOYMENT_ID}$"; then
    echo "❌ Agent ${ADK_DEPLOYMENT_ID} is already registered in the Agentspace app"
else
    echo "✅ Agent ${ADK_DEPLOYMENT_ID} not registered in the Agentspace app"
fi

```


### Register an agent
#### Without OAuth
```sh
curl -X POST -H "Authorization: Bearer $(gcloud auth print-access-token)" \
-H "Content-Type: application/json" \
-H "X-Goog-User-Project: ${PROJECT_NUMBER}" "${ENGINE_URL}/assistants/default_assistant/agents" \
-d '{
    "displayName": "'"${DISPLAY_NAME}"'",
    "description": "'"${DESCRIPTION}"'",
    "icon": {
        "uri": "'"${ICON_URI}"'"
    },
    "adk_agent_definition": {
        "tool_settings": {
            "tool_description": "'"${TOOL_DESCRIPTION}"'"
        },
        "provisioned_reasoning_engine": {
            "reasoning_engine": "projects/'"${PROJECT_ID}"'/locations/'"${REGION}"'/reasoningEngines/'"${ADK_DEPLOYMENT_ID}"'"
        }
    }
}'
```

#### Using OAuth
```sh
curl -X POST -H "Authorization: Bearer $(gcloud auth print-access-token)" \
-H "Content-Type: application/json" \
-H "X-Goog-User-Project: ${PROJECT_NUMBER}" "${ENGINE_URL}/assistants/default_assistant/agents" \
-d '{
    "displayName": "'"${DISPLAY_NAME}"'",
    "description": "'"${DESCRIPTION}"'",
    "icon": {
        "uri": "'"${ICON_URI}"'"
    },
    "adk_agent_definition": {
        "tool_settings": {
            "tool_description": "'"${TOOL_DESCRIPTION}"'"
        },
        "provisioned_reasoning_engine": {
            "reasoning_engine": "projects/'"${PROJECT_ID}"'/locations/'"${REGION}"'/reasoningEngines/'"${ADK_DEPLOYMENT_ID}"'"
        },
        "authorizations": [
            "projects/'"${PROJECT_ID}"'/locations/global/authorizations/'"${AUTH_ID}"'"
        ]
    }
}'
```

The response of the above command returns all fields of the created Agent resource. The fields are the same as supplied by the command with the addition of the “name” field: this is the resource name of the newly created agent resource, it can be used to reference the agent later (e.g. when updating it). An example resource name is "projects/PROJECT_ID/locations/global/collections/default_collection/engines/test-engine-1/assistants/default_assistant/agents/13570498627670476984”. The `AGENT_ID`, or agent resource ID is `13570498627670476984` in this example.

### Update an agent's registration
All of the fields that were supplied during agent registration can be updated. The following fields are mandatory during update: `displayName`, `description`, `tool_settings`, `reasoning_engine`. Even if they are unchanged they have to be provided again.

1. Get the agent resource ID from the get or list operation.
```sh
export AGENT_ID="123435678901234567890"  # replace with actual agent ID
```

2. Update the agent registration.
```sh
curl -X PATCH -H "Authorization: Bearer $(gcloud auth print-access-token)" \
-H "Content-Type: application/json" \
-H "X-Goog-User-Project: ${PROJECT_NUMBER}" "${ENGINE_URL}/assistants/default_assistant/agents/${AGENT_ID}" \
-d '{
    "displayName": "'"${DISPLAY_NAME}"'",
    "description": "'"${DESCRIPTION}"'",
    "adk_agent_definition": {
        "tool_settings": {
            "tool_description": "'"${TOOL_DESCRIPTION}"'"
        },
        "provisioned_reasoning_engine": {
            "reasoning_engine": "projects/'"${PROJECT_ID}"'/locations/'"${REGION}"'/reasoningEngines/'"${ADK_DEPLOYMENT_ID}"'"
        }
    }
}'
```

### Delete an agent
1. Get the agent resource ID from the get or list operation.
```sh
export AGENT_ID="123435678901234567890"  # replace with actual agent ID
```

2. Delete the agent using its ID.
```sh
curl -X DELETE -H "Authorization: Bearer $(gcloud auth print-access-token)" \
-H "Content-Type: application/json" \
-H "X-Goog-User-Project: ${PROJECT_NUMBER}" "${ENGINE_URL}/assistants/default_assistant/agents/${AGENT_ID}"
```

## Resources
- [Discovery Engine API | REST | Overview](https://cloud.google.com/generative-ai-app-builder/docs/reference/rest)
- Internal document: "How to register and use ADK Agents with Agentspace.pdf"

**[← Back to Documentation](../README.md#documentation)**
