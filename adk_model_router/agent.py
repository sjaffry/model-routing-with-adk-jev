"""ADK 2.0 Model Router Workflow using TypeSafe's Jev `TypesafeClassifier`.

Based on ADK 2.13.0 and TypeSafe's Jev `jev-latest`
- Uses `TypesafeClassifier` (`google.adk.integrations.typesafe`) backed by
  TypeSafe's `jev-latest` System-1 decision model (`/v1/systemone` API).
- Evaluates a typed `Choice` question (`google.adk.labs.classifiers`) in a
  single forward pass returning calibrated probabilities and a selected choice.
- Routes execution in an ADK 2.0 `Workflow` via `ClassifierNode` to either the
  `fast` or `powerful` `Agent`.
"""

from google.adk import Agent, Workflow
from google.adk.integrations.typesafe import TypesafeClassifier
from google.adk.labs.classifiers import Choice, ClassifierNode
from google.adk.workflow import START


classifier = TypesafeClassifier(
    model="jev-latest",  # Reads TYPESAFE_API_KEY from environment by default
)

ROUTING_QUESTION = Choice(
    instructions="Choose the least costly model that can complete the task.",
    criteria={
        "fast": "Direct lookups, extraction, and localized changes.",
        "powerful": "Architecture and high-stakes decisions.",
    },
)

fast_agent = Agent(
    name="fast_agent",
    model="gemini-2.5-flash",
    description="Fast, low-cost model for direct lookups, extraction, and localized changes.",
    instruction="Complete the user's request concisely and accurately.",
)

powerful_agent = Agent(
    name="powerful_agent",
    model="gemini-2.5-pro",
    description="Powerful model for architecture and high-stakes decisions.",
    instruction="Provide thorough architectural analysis and high-stakes reasoning.",
)


# ADK 2.0 Declarative Routing Node Powered by ClassifierNode + TypesafeClassifier (Jev)
typesafe_jev_router = ClassifierNode(
    name="typesafe_jev_router",
    description=(
        "Assesses the incoming prompt with Jev via TypesafeClassifier and "
        "routes to the selected model tier."
    ),
    classifier=classifier,
    question=ROUTING_QUESTION,
    answer_key="jev_routing",
)


agent = Workflow(
    name="adk_typesafe_model_router_workflow",
    description=(
        "ADK 2.0 Workflow that classifies prompts with TypeSafe's Jev decision "
        "model (TypesafeClassifier) and routes to the selected model tier."
    ),
    edges=[
        (
            START,
            typesafe_jev_router,
            {
                "fast": fast_agent,
                "powerful": powerful_agent,
            },
        ),
    ],
)

# Expose `root_agent` for `adk run` / `adk web` / `adk api_server` discovery
root_agent = agent
