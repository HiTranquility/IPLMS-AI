# Final Project Assignment: Guidelines
**New Technologies in Software Engineering · Academic year 2026–2027**

**What changed from last year:** AI is now the core of the product, not one feature added at the end. AI coding tools are allowed and encouraged. In return, every member must show that they understand the system from requirement to code, and the grade checks this directly.

---

## 1. General Scope

* Group size: **1–3 members**.
* Goal: build a working prototype of an **AI-powered application** that solves a real problem for a clear user group.
* The AI part must do real work in the product: answer from the app's own data, take actions through tools, or make decisions that users rely on. A chat box that only forwards messages to an LLM is not enough.
* Deliverables: working prototype, project documents, presentation, live defense with individual Q&A.

---

## 2. Project Topics

Each group proposes its own topic in Milestone 1. The topic must have a real user, a real problem, and data the AI can work with. Examples:

* **Course assistant** that answers students from lecture notes and the syllabus (RAG), and creates study plans with a calendar tool.
* **Customer support agent** for a small shop: answers from a product and policy knowledge base, checks order status through an API, and hands off to a human.
* **Recruitment helper** that reads CVs, scores them against a job description with structured output, and explains each score.
* **Smart expense tracker** that reads receipts from photos, categorizes spending, and answers questions in natural language about the user's own data.
* **Clinic or HR booking assistant** that books, changes and cancels appointments through tools, with confirmation before any change.

---

## 3. Technology Requirements

Note: Choose **either** a Web App or a Mobile App. Keep the stack simple so that most of your effort goes into the AI part and into understanding your own system.

### Frontend
* **Web:** React, Next.js, Angular, Vue, or Blazor. **Mobile:** Flutter, React Native, or .NET MAUI.
* Show at least **one modern feature**, for example streaming AI responses in the UI, SSR/SSG, PWA offline mode, or a device feature such as camera or GPS.

### Backend and Data
* One of: **Node.js (Express/NestJS), Python (FastAPI/Flask), ASP.NET Core, or Java Spring Boot**.
* **RESTful APIs** with at least basic CRUD, secured with **JWT**.
* A database (**SQL or NoSQL**). If you use RAG, also a **vector store** (pgvector, Chroma, Qdrant, FAISS, or a managed one).
* **All LLM API calls go through your backend.** API keys must never be in frontend code or in the Git repository.

### Integration and Deployment
* **OAuth2 login** (Google, GitHub or Facebook) with role-based access (at least admin and user).
* **Real-time** updates with WebSockets, SignalR, SSE or Firebase. Streaming the AI answer token by token counts.
* **Deployment:** Docker Compose locally, or free hosting (Vercel, Render, Railway, Firebase). The demo must run from the deployed or containerized version.

---

## 4. AI Requirements (Core)

### 4.1 AI Capabilities
Implement **at least two** of the following. Groups of 3 must implement **at least three**.

| Capability | What it must include |
| :--- | :--- |
| **A. RAG over app data** | Chunking, embeddings, vector search, and answers that show their sources. The bot must say it doesn't know when the answer is not in the data. |
| **B. Tool-using agent** | The LLM calls at least **3 tools** (functions or an MCP server) that read or change real app data. Any action that changes data must ask the user to confirm first. |
| **C. Structured output** | The LLM returns JSON validated against a schema (e.g. Pydantic, Zod), and the app uses the result in its logic, such as scoring, classifying, or extracting fields from documents. |
| **D. Multimodal input** | Images, PDFs or voice are processed by AI (e.g. receipt reading, document extraction, speech-to-text), and the result is stored and used by the app. |
| **E. Multi-agent workflow** | Two or more agents with different roles (e.g. planner and checker) and a clear hand-off between them, shown in logs. |

### 4.2 Engineering the AI (required for every group)
* **Model choice:** explain which model you use and why (quality, cost, speed, privacy). You may use cloud APIs (OpenAI, Gemini, Claude, OmniRoute, etc.) or a local model (Ollama, LM Studio).
* **Prompt management:** prompts are stored in files or config, with version history in Git, not hard-coded across the code.
* **Guardrails:** handle at least these three risks: (1) a prompt injection attempt, (2) a request outside the app's scope, (3) a wrong or failed AI response (timeout, invalid JSON, empty answer). Show each one in the demo.
* **Evaluation set:** at least **20 test cases** with expected results (normal, edge and should-refuse cases). Run them and report the pass rate before and after at least one improvement.
* **Logging and cost:** log each AI request (prompt version, tools called, tokens, latency). Show the average cost and response time per request.
* **Fallback:** if the AI service is down, the app still works for its non-AI features and shows a clear message.

---

## 5. Understanding What You Build

You may use AI coding tools (Copilot, Cursor, Claude Code, ChatGPT, etc.) for any part of the project. The rules below make sure you still understand your system from requirement to code.

### 5.1 Requirement Traceability
* Write **8–15 user stories**, each with acceptance criteria.
* Keep a **traceability table**: User story → API endpoint or component → source file(s) → test case(s). You must be able to open the code for any story when asked.

### 5.2 Design Decisions
* An **architecture diagram** that shows the frontend, backend, database, vector store, LLM provider and the data flow of one AI request.
* At least **3 Architecture Decision Records (ADRs)**: short notes on a decision, the options you considered, and why you chose one. At least one must be about the AI design (e.g. chunk size, model choice, tool design).

### 5.3 AI Usage Log
* A file **AI_USAGE.md** in the repo that lists the main parts generated with AI tools, the tool used, the key prompt, and **what you checked or changed** in the generated code.
* Include at least **2 cases where AI-generated code was wrong** or not good enough, and how you found and fixed it.
* Using AI tools without listing them in the log counts as academic misconduct.

### 5.4 Ownership
* Each member **owns at least one module** (e.g. RAG pipeline, agent tools, auth, frontend chat UI) and is the first person to answer questions about it.
* Git history must show commits from every member. A member with almost no commits must explain why in the report.

---

## 6. Functional Requirements
* **User management:** OAuth2 + JWT, role-based access (admin/user).
* **Minimum features:**
  1. CRUD for the main data of your app (posts, tasks, products, documents, etc.).
  2. Search, filter and sort with pagination.
  3. Real-time updates or streaming.
  4. File upload, used as input for the AI where possible.
  5. The AI capabilities from Section 4.
  6. An admin dashboard that includes AI usage: number of requests, cost, average latency, and failed or refused requests.

---

## 7. Non-Functional Requirements
* Responsive UI (desktop and mobile view).
* Data stored persistently in the database.
* **Security:** no secrets in the repo, input validation on every API, and users can only see their own data (also inside RAG search results).
* **Privacy:** state what user data is sent to the LLM provider and how you limit it.
* **Testing:** unit tests for core business logic, plus the AI evaluation set from Section 4.2.

---

## 8. Milestones

| Milestone | When | What to submit |
| :--- | :--- | :--- |
| **M1: Proposal** | Week [__] | Topic, users and problem; 8–15 user stories; chosen AI capabilities; first architecture sketch. |
| **M2: Mid-point demo** | Week [__] | One AI capability working end to end; first 10 evaluation cases; at least 1 ADR; AI_USAGE.md started. |
| **M3: Final defense** | Week [__] | Everything in Section 9. |

---

## 9. Final Deliverables
* **Git repository** with a README: how to run (Docker or deployed link), environment variables needed (without values), and test accounts.
* **Project report** (PDF, 10–20 pages): user stories and traceability table, architecture diagram, ADRs, AI design (prompts, tools, RAG settings), evaluation results, cost and latency summary, limitations.
* **AI_USAGE.md** in the repo (Section 5.3).
* **Presentation slides** (maximum 15 slides).
* **Demo video** (3–5 minutes) as a backup in case the live demo fails.

---

## 10. Final Defense (about 30 minutes per group)

| Part | Time | What happens |
| :--- | :--- | :--- |
| **Demo** | 8 min | The group shows the main user flow and the AI features, including at least one guardrail case. |
| **Live change** | 10 min | The lecturer asks for a small change (e.g. add a tool, change a prompt rule, change the chunk size, add a field to the structured output). The owner of that module makes it, with AI tools allowed, while explaining each step. |
| **Individual Q&A** | 12 min | Each member answers questions on their own module and on one other part chosen by the lecturer: trace a user story to code, explain a design decision, explain why an AI test case fails. |

Every member must be present. A member who cannot attend the defense without a valid reason receives zero for the individual part.

---

## 11. Evaluation Criteria

| Criteria | Weight | Details |
| :--- | :--- | :--- |
| **Requirements & Design** | 15% | Clear user stories and acceptance criteria, traceability table, architecture diagram, ADRs. |
| **Technical Implementation** | 15% | Frontend, backend, database, OAuth2/JWT, real-time, deployment; code quality and security. |
| **AI Features** | 25% | Required capabilities (Section 4.1) work well and are useful to the user, not decoration. |
| **AI Quality & Safety** | 10% | Evaluation set and results, guardrails, logging, cost and fallback (Section 4.2). |
| **Demo & Presentation** | 10% | Clear demo and slides; the live change request is completed. |
| **Individual Understanding** | 20% | Scored for each member separately: Q&A, explaining own module, tracing a story to code, AI_USAGE.md quality. |
| **UI/UX** | 5% | Responsive, easy to use, clear AI states (loading, streaming, errors, sources). |

### Individual grading rules
* All criteria except Individual Understanding give a **group score** (80%) that every member shares. Individual Understanding (20%) is a **personal score** for each member.
* **Understanding gate:** if a member cannot explain their own module or trace one of its user stories to the code, that member's final score is **capped at 50%** of the group score, even if the product works well.
* Missing or clearly incomplete AI_USAGE.md: **minus 10%** for the group.
* Secrets (API keys, passwords) found in the Git history: **minus 5%** for the group.
