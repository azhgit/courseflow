"""Pre-cached demo questions for quota bypass.

Provides 10 demo questions with pre-computed answers for demonstration purposes.
Cached responses bypass both per-IP hourly limits and daily budget quotas.
"""

from src.courseflow.domain.models import DemoCacheEntry

# 10 pre-cached demo questions across diverse topics
DEMO_CACHE: list[DemoCacheEntry] = [
    DemoCacheEntry.create(
        question="What is async/await in Python?",
        answer="Async/await is Python's syntax for writing asynchronous code. "
        "It allows you to write non-blocking code that pauses execution at await points, "
        "letting other tasks run. Key points: async def creates a coroutine, "
        "await pauses execution until the awaited coroutine completes, "
        "it's built on top of asyncio library. Example: async def fetch(): return await get_data()",
        subject="python",
    ),
    DemoCacheEntry.create(
        question="How does Retrieval Augmented Generation (RAG) work?",
        answer="RAG combines a retrieval system with a language model. The process: "
        "(1) User submits query; (2) Retrieval system searches knowledge base for relevant documents; "
        "(3) Retrieved documents are concatenated as context; (4) LLM generates answer using context. "
        "Benefits: Answers grounded in actual data, reduced hallucinations, up-to-date information. "
        "Example: CourseFlow uses ChromaDB for retrieval and Gemini for generation.",
        subject="ai",
    ),
    DemoCacheEntry.create(
        question="What is photosynthesis?",
        answer="Photosynthesis is the process by which plants convert light energy into chemical energy. "
        "The main equation: 6CO2 + 6H2O + light → C6H12O6 + 6O2. Light reactions occur in thylakoids, "
        "producing ATP and NADPH. Calvin cycle (dark reactions) uses these to build glucose. "
        "Key enzyme: RuBisCO. Occurs in chloroplasts. Essential for Earth's oxygen production.",
        subject="biology",
    ),
    DemoCacheEntry.create(
        question="What was the French Revolution?",
        answer="The French Revolution (1789-1799) was a period of social upheaval in France. "
        "Key causes: feudal system, enlightenment ideas, financial crisis. Major events: Storming of Bastille (1789), "
        "Declaration of Rights of Man (1789), reign of terror (1793-1794). Outcomes: abolition of feudalism, "
        "rise of nationalism, Napoleonic era. Impact: influenced democratic movements worldwide.",
        subject="history",
    ),
    DemoCacheEntry.create(
        question="How do machine learning models learn from data?",
        answer="ML models learn by minimizing a loss function during training. Process: "
        "(1) Initialize parameters randomly; (2) Forward pass: compute predictions; "
        "(3) Calculate loss (difference from actual labels); (4) Backpropagation: compute gradients; "
        "(5) Update parameters using gradient descent. Repeat until convergence. "
        "Common optimizers: SGD, Adam. Prevents overfitting with regularization and validation sets.",
        subject="ai",
    ),
    DemoCacheEntry.create(
        question="What are mitochondria?",
        answer="Mitochondria are the powerhouses of the cell. They convert glucose into ATP through "
        "cellular respiration. Structure: outer membrane, inner membrane, matrix, cristae. "
        "Process: glycolysis (cytoplasm) → Krebs cycle (matrix) → electron transport chain (inner membrane). "
        "Produces 30-32 ATP per glucose. Also involved in: calcium regulation, heat production, apoptosis. "
        "Contain their own DNA—evidence of endosymbiotic origin.",
        subject="biology",
    ),
    DemoCacheEntry.create(
        question="How does the internet work?",
        answer="The internet connects computers globally via standardized protocols. "
        "Layers (TCP/IP model): Physical (cables), Data Link (MAC), Network (IP routing), "
        "Transport (TCP/UDP), Application (HTTP/DNS/SMTP). Process: DNS resolves domain to IP, "
        "TCP establishes connection, HTTP requests sent, packets routed via BGP, responses assembled. "
        "HTTPS adds encryption. Edge computing and CDNs optimize delivery.",
        subject="programming",
    ),
    DemoCacheEntry.create(
        question="What is quantum computing?",
        answer="Quantum computing uses quantum bits (qubits) that exploit superposition and entanglement. "
        "Key differences from classical: qubits can be 0, 1, or both (superposition); "
        "entanglement links qubits; quantum gates perform operations. Advantages: exponential speedup for specific problems "
        "(factoring, optimization, simulation). Challenges: decoherence, error rates, limited qubit counts. "
        "Current hardware: superconducting qubits, trapped ions, photonic.",
        subject="ai",
    ),
    DemoCacheEntry.create(
        question="What causes climate change?",
        answer="Climate change is primarily caused by human-induced greenhouse gas emissions. "
        "Main gases: CO2 (combustion), CH4 (livestock, fossil fuels), N2O (agriculture). "
        "Mechanism: these gases trap heat in atmosphere, increasing surface temperature. "
        "Consequences: rising sea levels, extreme weather, ecosystem disruption, human health impacts. "
        "Solutions: renewable energy, carbon pricing, reforestation, energy efficiency.",
        subject="biology",
    ),
    DemoCacheEntry.create(
        question="How does REST API design work?",
        answer="REST (Representational State Transfer) is an architectural style for web APIs. "
        "Principles: resources (nouns), standard methods (GET/POST/PUT/DELETE), stateless communication, "
        "proper HTTP status codes. Example endpoint: GET /api/v1/users/123 retrieves user 123. "
        "Best practices: consistent URL structure, versioning (/v1/), filtering/sorting parameters, "
        "pagination, HATEOAS links, proper authentication (OAuth2), comprehensive documentation.",
        subject="programming",
    ),
]


def get_cached_question_by_text(question: str) -> DemoCacheEntry | None:
    """Find a cached question by normalized text match.

    Args:
        question: User question text

    Returns:
        DemoCacheEntry if match found, None otherwise
    """
    for entry in DEMO_CACHE:
        if entry.matches(question):
            return entry
    return None


def get_all_cached_questions() -> list[DemoCacheEntry]:
    """Get all cached demo questions.

    Returns:
        List of all DemoCacheEntry objects
    """
    return DEMO_CACHE.copy()
