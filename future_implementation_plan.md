# Clemta Bot - GitHub Insights & Upgrade Plan

We researched how developers on GitHub are building advanced AI Email Auto-responders (using Gmail API + LLMs). Based on popular open-source repositories and architectures, here are the major insights and potential upgrade paths for the `clemta-bot` project.

## GitHub Insights & Industry Patterns

1. **RAG (Retrieval-Augmented Generation) for Knowledge Injection:**
   * *How others do it:* Projects like `Gmail-RAG-automation` use vector databases (Pinecone/Chroma) to store PDF documents, FAQs, and pricing tables. When an email arrives, the bot searches this database for relevant context and injects it into the LLM prompt.
   * *Why it's good:* Prevents hallucinations and allows the bot to answer highly specific technical or pricing questions accurately based on company documents.

2. **Human-in-the-Loop (Approval Workflows):**
   * *How others do it:* Instead of directly replying, the bot creates a **Draft** in Gmail or sends a notification to a Discord/Slack channel with the generated response. A human clicks "Approve" or edits it before sending.
   * *Why it's good:* Zero risk of the AI sending something inappropriate or wrong to an important client.

3. **Multi-Agent Triage (Routing & Labeling):**
   * *How others do it:* Projects using LangChain/CrewAI have an initial "Triage Agent". This agent reads the email and assigns Gmail labels (e.g., `Urgent`, `Spam`, `Sales`, `Support`). It only triggers the "Reply Agent" if the email is a genuine support/sales inquiry.
   * *Why it's good:* Keeps the inbox extremely organized and saves LLM API costs by not processing junk/newsletters deeply.

## Proposed Changes (Pick your preferred path)

We can upgrade `clemta-bot` with one or more of these features. 

### Path A: The "Safe & Enterprise" Upgrade (Drafts + Labels)
- Modify the bot so it **creates drafts** instead of sending emails directly (`messages().drafts().create()`).
- Add an AI classification step that applies a Gmail Label (e.g., "AI Drafted") to the email so you know it's ready for review.

### Path B: The "Knowledgeable" Upgrade (RAG)
- Create a `knowledge/` folder.
- Add an integration (using a lightweight local vector store or basic text search) so the bot reads company PDFs/Texts before answering.

### Path C: The "Multi-Agent" Upgrade
- Add a preprocessing step where Gemini first outputs a JSON classification (`{"category": "spam/sales/support", "urgency": "1-5"}`).
- The bot applies Gmail labels based on this JSON, and only generates full replies for `sales/support` emails.

---

## User Review Required

> [!IMPORTANT]
> Please review the insights above. Which upgrade path (or combination) excites you the most for the next version of `clemta-bot`? Should we implement Draft creation, RAG knowledge bases, or smart labeling? 

## Verification Plan

### Automated Tests
- If we implement Drafts: Test by sending an email and verifying via Gmail API that a draft was created and the email is labeled correctly.
- If we implement RAG: Add mock pricing data to a document, ask a pricing question, and verify the AI quotes the document exactly.

### Manual Verification
- User will send test emails from an external account and observe the bot's new behavior (whether it creates a draft, applies a label, or quotes a specific injected document).
