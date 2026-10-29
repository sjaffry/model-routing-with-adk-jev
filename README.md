# ADK 2.0 Model Router with TypeSafe Jev (`TypesafeClassifier`)

Cost-aware prompt routing in **Google ADK (`>= 2.13.0`)** using **TypeSafe's Jev** System-1 decision model (`TypesafeClassifier`) to dynamically route requests between fast and frontier Gemini models.

## Overview

Traditional LLM routers require a full text-generation round-trip just to decide which downstream model should handle a request. This example ([`adk_model_router/agent.py`](adk_model_router/agent.py)) replaces LLM-based routing with `TypesafeClassifier` (`google.adk.integrations.typesafe`) and `ClassifierNode` (`google.adk.labs.classifiers`), introduced in `google-adk` **2.13.0**.

Instead of generating tokens, Jev (`jev-latest`) evaluates a typed `Choice` question (`google.adk.labs.classifiers`) in a **single forward pass** via TypeSafe's `/v1/systemone` API—returning calibrated probabilities, a confidence score, and the selected model tier (`fast` or `powerful`) to branch execution inside a declarative ADK 2.0 `Workflow`.

---

## Workflow Architecture

```mermaid
flowchart TD
    START(["START"]) --> Router["typesafe_jev_router<br/>ClassifierNode (jev-latest)"]
    Router -- "fast" --> Fast["fast_agent<br/>(gemini-2.5-flash)"]
    Router -- "powerful" --> Powerful["powerful_agent<br/>(gemini-2.5-pro)"]
```

### Routing Tiers

| Route | Target Agent | Model | Routing Criteria (`ROUTING_QUESTION`) |
| :--- | :--- | :--- | :--- |
| `fast` | `fast_agent` | `gemini-2.5-flash` | Direct lookups, extraction, and localized changes. |
| `powerful` | `powerful_agent` | `gemini-2.5-pro` | Architecture and high-stakes decisions. |

---

## How It Works

The implementation in [`adk_model_router/agent.py`](adk_model_router/agent.py) is organized into four stages:

1. **Classifier & Typed Routing Question (`TypesafeClassifier` & `Choice`)**:
   - Configures `TypesafeClassifier(model="jev-latest")`, which authenticates using `TYPESAFE_API_KEY` from the environment.
   - Defines `ROUTING_QUESTION` as a `Choice` question instructing Jev to *"Choose the least costly model that can complete the task"* across the `fast` and `powerful` criteria.

2. **Target Model Agents (`Agent`)**:
   - **`fast_agent` (`gemini-2.5-flash`)**: Handles low-latency, low-cost tasks concisely and accurately.
   - **`powerful_agent` (`gemini-2.5-pro`)**: Handles complex architectural design and high-stakes reasoning.

3. **Jev Routing Node (`ClassifierNode` as `typesafe_jev_router`)**:
   - Implements ADK's declarative `ClassifierNode` (`google.adk.labs.classifiers`) configured with `classifier=classifier`, `question=ROUTING_QUESTION`, and `answer_key="jev_routing"`.
   - Assesses the incoming prompt via Jev in a single forward pass without manual token generation or parsing.
   - Automatically saves Jev's classification result into session state under `answer_key="jev_routing"`.
   - Emits the chosen route label (`"fast"` or `"powerful"`) to resolve downstream workflow branching.

4. **Declarative Workflow Graph (`Workflow` & `root_agent`)**:
   - Defines `agent = Workflow(name="adk_typesafe_model_router_workflow", edges=[(START, typesafe_jev_router, {"fast": fast_agent, "powerful": powerful_agent})])`.
   - Wires `START -> typesafe_jev_router` with dictionary-based conditional edges mapping Jev's output choices directly to `fast_agent` and `powerful_agent`.
   - Exposes `root_agent = agent` (re-exported in [`adk_model_router/__init__.py`](adk_model_router/__init__.py)) for ADK CLI (`adk run`) and web server (`adk web`) discovery.

### Session State Telemetry

On every turn, `typesafe_jev_router` records Jev's decision metadata into `ctx.state["jev_routing"]` (inspectable in the `adk web` State tab):

| State Attribute (`ctx.state["jev_routing"]`) | Type | Description |
| :--- | :--- | :--- |
| `choice` | `str` | Selected route tier (`"fast"` or `"powerful"`). |
| `probabilities` | `dict[str, float]` | Calibrated probability distribution across `"fast"` and `"powerful"`. |
| `confidence` | `float` or `None` | Confidence score reported by Jev for the classification. |
| Model metadata | `dict` or `str` | Additional System-1 inference metadata returned by Jev `/v1/systemone`. |

---

## Prerequisites & Setup

### 1. Create Virtual Environment & Install Dependencies

Requires Python `>= 3.11` and `google-adk >= 2.13.0`. From the `model-routing-with-adk-jev/` project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install "google-adk>=2.13.0"
```

### 2. Configure Environment Variables

Configure the `.env` file in the `model-routing-with-adk-jev/` root directory (or export in your shell) with your TypeSafe and Gemini credentials:

```bash
# Required by TypesafeClassifier
TYPESAFE_API_KEY=your_typesafe_api_key

# Option A: Google AI Studio
GOOGLE_GENAI_USE_ENTERPRISE=FALSE
GOOGLE_API_KEY=your_gemini_api_key

# Option B: Vertex AI (instead of Option A)
# GOOGLE_GENAI_USE_ENTERPRISE=TRUE
# GOOGLE_CLOUD_PROJECT=your-gcp-project
# GOOGLE_CLOUD_LOCATION=us-central1
```

---

## Running the Router

Run the commands below from the `model-routing-with-adk-jev/` root directory (with `.venv` activated):

**Interactive CLI:**

```bash
adk run adk_model_router
```

**ADK Web UI (recommended for inspecting graph routing & Jev probabilities):**

```bash
adk web
```

Then select **`adk_model_router`** from the agent dropdown in the web UI.

### Example Prompts to Try

- **Routes to `fast` (`gemini-2.5-flash`)**:
  > *"Extract all dates and dollar amounts from: Invoice #402 paid $1,250 on Oct 14, 2026."*
- **Routes to `powerful` (`gemini-2.5-pro`)**:
  > *"Design a multi-region active-active payment ledger architecture with strict idempotency and zero-RPO failover."*

---

## Project Structure

```text
model-routing-with-adk-jev/
├── .env                  # Environment variables (TYPESAFE_API_KEY, Gemini/Vertex credentials)
├── .venv/                # Python virtual environment
├── README.md             # Project documentation
└── adk_model_router/     # ADK agent package
    ├── __init__.py       # Re-exports root_agent for ADK CLI discovery
    └── agent.py          # TypesafeClassifier (Jev) router node, Gemini tier agents, and Workflow graph
```
