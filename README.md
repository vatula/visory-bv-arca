# Prototype: Autonomous Reconciliation and Contextual Resolution Agent (ARCRA)

## Strategic Product Thinking and Gap Identification

The target application selected for this blueprint is Xero, 
the dominant cloud accounting platform in the Australian market.

While Xero has recently announced "JAX" (Just Done with your control), an AI superagent designed to automate routine tasks, 
critical analysis of the current accounting software landscape reveals a glaring functional void.

Current tools are proficient at processing perfectly formatted data, 
but they fail entirely when confronted with unstructured ambiguity. 
The most persistent, time-consuming bottleneck in financial operations 
is the asynchronous chase for missing context.

When a transaction appears on a _corporate card feed_ lacking a _receipt_, 
or when _an invoice description_ is _too vague_ to determine the correct _general ledger (GL) code_, 
the automation halts. A human bookkeeper must transition across multiple applications--
searching email inboxes, 
querying corporate knowledge bases like Notion for expense policies, 
and pinging employees on Slack—to piece together the narrative of the expense. 
The missing feature is a system capable of executing this multi-system traversal autonomously.

The proposed prototype is the **Autonomous Reconciliation and Contextual Resolution Agent (ARCRA)**. 
ARCRA is an agentic workflow orchestration engine, powered by MCP, 
that detects anomalies in the Xero ledger and autonomously navigates external enterprise 
tools to gather context, resolve ambiguity, and prepare the transaction for final human approval.

## Storyboarding the Agentic User Experience

ARCRA is designed to elevate human accountants to the role of an auditor and final decision-maker, 
aligning with the concept of verifiable, accountable intelligence.

The workflow is initiated when the system ingests a batch of daily bank feed transactions. 
The logic engine flags a specific entry: a $4,500 debit to "Acme Cloud Services" 
executed by an employee named Alice, which lacks a matching invoice in the system.

1. **Anomaly Detection and Orchestration Initiation:** ARCRA identifies the un-reconciled transaction. The central Python-based orchestrator, powered by an advanced reasoning model, formulates a multi-step resolution plan.
2. **Policy Verification:** The agent determines it must first understand the organizational rules regarding software expenditures. It invokes a locally hosted Notion MCP Server, executing a semantic search query against the corporate wiki for "IT Procurement Policy and Expense Limits". The server returns the policy, which states that cloud expenses over $2,000 require a specific project code.
3. **Document Retrieval:** Understanding that the invoice might have been auto-saved but not uploaded to the accounting software, ARCRA invokes the Google Drive MCP Server. It uses the searchFiles tool to look for PDF documents containing the string "Acme Cloud Services" modified within the last seven days. In this scenario, the search yields no results.
4. **Asynchronous Intervention:** Failing to find the documentation autonomously, ARCRA recognizes that it must interface with a human. It queries the Xero contact database to identify the Slack handle associated with the corporate cardholder. ARCRA then invokes the Slack MCP Server to send a direct, contextualized message: "Hi Alice, I am attempting to reconcile a $4,500 charge to Acme Cloud on your corporate card from Tuesday. I could not locate the invoice in the shared drive, and per company policy, this requires a project code. Could you please reply with the invoice and the relevant code?".
5. **Stateful Suspension and Resumption:** The agentic loop enters a suspended state, awaiting external input without consuming active compute resources.
6. **Context Synthesis and Xero Ledger Update:** Upon receiving a reply from Alice containing the PDF and the text "Project Phoenix," ARCRA resumes. It utilizes an internal vision model to extract the line items from the PDF. It then invokes the Xero MCP Server, utilizing the `createDraftInvoice` tool to generate a fully populated, coded draft bill in the accounting system, attaching the PDF as supporting evidence.
7. **Human Validation:** The human bookkeeper logs into the Visory platform dashboard, reviews the drafted entry alongside the full audit trail of ARCRA's investigation, and clicks "Approve".

## Technical Architecture and Execution Strategy

The architecture relies on a hybrid stack that 
leverages the strongest attributes of both Python and TypeScript.

The system is decoupled into two primary layers: the Orchestration Engine and the MCP Service Mesh.

1. **The Orchestration Engine (Python):** The central agent is built utilizing PydanticAI. The framework allows the engineer to define the agent as a state machine (a directed acyclic graph), which is absolutely critical for managing the long-running, multi-step financial workflows required by ARCRA. By treating the agentic loop as a graph, the application can reliably suspend execution to wait for a Slack message, persist the state to a lightweight local database (such as SQLite), and resume flawlessly without losing the context of the investigation. The orchestration engine acts as the MCP Client, establishing connections to the various external servers.
2. **The MCP Service Mesh (TypeScript):** While the orchestrator is written in Python, the individual Model Context Protocol servers are implemented using TypeScript (Node.js). TypeScript is chosen for the execution layer because its robust static typing ensures that the JSON schemas defining the MCP tools are mathematically rigorous, preventing the AI from generating malformed API payloads.
