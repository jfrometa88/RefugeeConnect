# RefugeeConnect AI: A Multi-Agent System to Help Migrants and Asylum Seekers Navigate Support Networks in Spain

**Track:** Digital Equity & Inclusivity | **Model:** Gemma 4

---

## The Problem: A Fragmented System That Fails the Most Vulnerable

Every year, thousands of people arrive in Spain fleeing conflict, poverty, or political persecution. They encounter a complex ecosystem of support organizations — Cruz Roja, Cáritas, ACNUR, CEAR, ACCEM, municipal social services — that theoretically covers most of their needs. In practice, however, this ecosystem is deeply fragmented: organizations operate without centralized or coordinated information systems, guidance quality varies dramatically depending on which specific branch a person visits, and most resources are only available in Spanish — creating an additional barrier for those who need help the most.

This project was not born from a theoretical analysis. The author arrived in Spain as a Cuban political asylum seeker, without family or financial support, and personally experienced every one of these barriers. The experience of visiting one Cruz Roja branch that could not provide guidance, then finding help at a different branch of the same organization, is not an edge case — it is the norm for thousands of people navigating this system each year.

The target population faces compounding disadvantages: language barriers, limited familiarity with Spanish bureaucracy, digital literacy gaps, and the psychological burden of precarious legal status. Traditional solutions — static websites, PDF guides, or phone hotlines — are insufficient for people who may not know what questions to ask, what documents they need, or even what services exist.

---

## The Solution: A Multi-Agent AI System with Human-Centered Design

RefugeeConnect AI addresses this problem through two complementary interfaces built on a shared knowledge base:

**Direct Dashboard Mode** provides immediate access to a curated database of organizations, services, requirements, and locations through an interactive map powered by OpenStreetMap. Users can filter by city, service type, language of service, and specific requirements without requiring AI interaction — ensuring the system remains useful even in low-connectivity or low-literacy contexts.

**AI Conversational Assistant Mode** allows users to describe their situation in natural language, in their own language, and receive personalized guidance. The system identifies their profile, maps their needs to available services, and provides step-by-step actionable instructions — what organization to go to, what to bring, what to say, what to expect.

A configurable model selector allows the system to run Gemma 4 locally via Ollama (for privacy-sensitive contexts or offline use) or via the Google AI Studio API (for higher capability in connected environments).

---

## Technical Architecture

### Why Gemma 4

Gemma 4's open architecture is central to this project's design philosophy. The target deployment context — NGOs, local social services, community centers — often involves resource-constrained hardware, privacy requirements around sensitive personal data, and limited IT infrastructure. Gemma 4's ability to run locally via Ollama on modest hardware makes it uniquely appropriate for this use case in a way that proprietary cloud-only models are not.

The E2B and E4B variants run on CPU-accessible hardware, enabling potential future deployment on edge devices. The 27B variant, accessible via Google AI Studio, provides the deeper reasoning required for complex multi-need cases involving legal status, bureaucratic requirements, and multilingual interaction.

Gemma 4's native function calling capability is used throughout the agent architecture to enable structured, reliable tool invocation — a critical requirement for a system where accuracy directly affects vulnerable people's access to help.

### Multi-Agent Architecture with Google ADK

The system uses Google's Agent Development Kit (ADK) to implement a three-tier agent hierarchy:

**Orchestrator Agent** receives the user's natural language input, identifies the core needs and user profile (language, location, document status, urgency), and delegates to specialized sub-agents. It maintains session memory to handle multi-turn conversations without requiring the user to repeat context.

**Needs Agent** queries the SQLite knowledge base to identify which services and organizations match the user's identified needs. Its tool (`services_tool`) performs structured queries filtering by service category, requirements, and availability.

**Geolocation Agent** filters available options by proximity to the user's location. Its tool (`location_tool`) queries the branches table with coordinates and calculates distance rankings, integrating with the OpenStreetMap frontend to update the map in real time.

**Guidance Agent** synthesizes the outputs from the previous agents into a final response, adapted to the user's language and literacy level. It generates actionable, step-by-step instructions that go beyond listing organizations — it tells users what to say, what documents to bring, and what to expect at each step.

### Knowledge Base Design

The SQLite database is structured to capture the operational reality of support organizations in Spain, not just their stated services. Key design decisions include:

- Separate `organizations` and `branches` tables to reflect that guidance quality and service availability vary by physical location, not just by organization.
- `organization_services` junction table with `requirements` and `notes` fields to capture the fine-grained conditions under which services are actually available (e.g., "only for asylum seekers with OAR appointment", "requires municipal empadronamiento").
- `languages_served` table to enable reliable filtering by the language of service — a first-order concern for the target population.

### Technology Stack

| Layer | Technology |
|-------|------------|
| Frontend | Plotly Dash, Dash Leaflet (OpenStreetMap) |
| Backend API | FastAPI (async) |
| Agent Framework | Google ADK |
| Model | Gemma 4 via Ollama (local) or Google AI Studio (API) |
| Database | SQLite |
| Containerization | Docker + Docker Compose |
| CI/CD | GitHub Actions |
| Deployment | Hugging Face Spaces |

---

## Implementation Highlights

### Dual Inference Mode

A configurable toggle in the Dash interface allows switching between local Ollama inference and Google AI Studio API at runtime, controlled via a FastAPI endpoint that updates the agent configuration. This design choice reflects a real-world deployment consideration: organizations with strict data privacy requirements (handling sensitive personal information about asylum seekers) may require fully local processing, while others may prioritize response quality.

### Multilingual Response

The Guidance Agent is instructed to detect the language of the user's input and respond in the same language, regardless of the language in which the underlying database and system prompts are written. This is implemented through Gemma 4's multilingual capabilities without requiring separate model instances per language — a practical requirement for deployment at scale.

### Separation of AI and Data Layers

Following an architecture pattern proven in the author's previous ADK projects, the Dash frontend and SQLite database operate independently of the AI layer. The dashboard's direct query mode functions without any AI involvement, ensuring that infrastructure failures or API limits in the AI layer do not render the entire system unusable. This resilience is particularly important for organizations that may depend on the system as a critical tool.

---

## Challenges and Design Decisions

<!-- TO BE COMPLETED: Add real challenges encountered during implementation -->

**Challenge 1: Knowledge base accuracy**
The effectiveness of the system depends entirely on the quality and currency of the organizational data. For the hackathon prototype, data was manually curated from official organization websites and direct knowledge of the Spanish support ecosystem. A production deployment would require a collaborative update mechanism involving the organizations themselves.

**Challenge 2: Handling ambiguous or incomplete user input**
<!-- Document how the orchestrator handles cases where user provides insufficient information -->

**Challenge 3: Local model performance on resource-constrained hardware**
<!-- Document observations on Gemma 4 E2B/E4B performance via Ollama -->

---

## Results and Impact

<!-- TO BE COMPLETED: Add real usage scenarios and demo results -->

The system was tested against five representative user scenarios:

1. Person without documentation seeking regularization guidance
2. Non-Spanish speaker seeking emergency medical attention
3. Family seeking emergency shelter
4. Person seeking legal advice on asylum application status
5. Person seeking employment or vocational training resources

<!-- Add qualitative results: response quality, language accuracy, routing correctness -->

---

## Real-World Applicability and Scalability

The prototype demonstrates viability at city scale (Madrid, Barcelona, Valencia, Seville, Bilbao) with approximately 20 organizations. The architecture scales horizontally: expanding coverage requires only populating additional rows in the database, with no architectural changes.

Organizations could self-manage their information through a simple admin interface (not implemented in the prototype), reducing the maintenance burden. The Docker-based deployment enables installation in organizational IT environments with minimal configuration.

The most significant barrier to real-world deployment is not technical but organizational: achieving the cooperation of the organizations themselves to maintain accurate, current data. This is a governance challenge that technology can support but not solve alone.

---

## Conclusion

RefugeeConnect AI demonstrates that open, locally-deployable AI models like Gemma 4 can address real social problems in contexts where proprietary cloud-only solutions are inappropriate due to cost, privacy, or connectivity constraints. The multi-agent architecture built on Google ADK provides a flexible, extensible foundation that can grow with the needs of the organizations and populations it serves.

The system does not attempt to replace human guidance — it attempts to ensure that the quality of guidance a person receives does not depend on which branch they happen to walk into, or whether a knowledgeable volunteer happened to be present that day.

---

## Resources

- **Live Demo**: [URL — to be added]
- **Code Repository**: [GitHub URL — to be added]
- **Demo Video**: [YouTube URL — to be added]
- **Kaggle Notebook**: [Kaggle URL — to be added]

---

*Word count: ~1,100 words (limit: 1,500)*
