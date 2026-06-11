Software Engineer Take-Home Assessment 
LangGraph Hybrid Chatbot: Insurance Quotation Assistant 
Role: Mid-Level Software Engineer 
Time Limit: 24 hours from receipt 
Deliverables: Working code repository 
AI Tools: Allowed (see note in Section 9 
1. Overview 
Build an insurance quotation assistant using LangGraph that combines conversational AI 
(answering questions about insurance products via RAG with transactional capabilities 
(collecting customer information and generating a quote through a structured workflow). 
The bot should use a state machine as its orchestrator to route user intent to the right 
flow. 
We are not looking for a production-ready product. We want to see how you design state transitions, handle the boundary between free-form conversation and structured 
transactions, and how quickly you can build something coherent with an unfamiliar 
framework. 
2. The Scenario 
Your chatbot is an AI assistant for a fictional insurance company called “Ivory 
Insurance.ˮ Ivory offers three types of insurance: auto, home, and life. The 
assistant helps prospective customers learn about these products and get personalized 
quotes. 
Your chatbot must support two modes of interaction: 
2.1 Conversational Mode RAG 
The user asks general questions about Ivoryʼs insurance products. The bot retrieves relevant information from your knowledge base and responds naturally. Examples: 
• “What types of insurance do you offer?ˮ
• “What does your auto policy cover?ˮ 
• “Do you cover pre-existing conditions on life insurance?ˮ 
• “Whatʼs the difference between comprehensive and third-party auto coverage?ˮ 
2.2 Transactional Mode Quotation Flow) 
The user wants to get a personalized insurance quote. The bot should guide them through a structured workflow to collect the required information, then generate a quote. The flow should include at minimum: 
1. Identify insurance type — which product does the user want a quote for (auto, 
home, or life)? 
2. Collect customer details — gather the relevant information for that product type. 
For example: 
◦ Auto: vehicle year/make/model, driver age, driving history, desired 
coverage level 
◦ Home: property type, location, estimated value, desired coverage level 
◦ Life: age, health status, coverage amount, term length 
3. Validate inputs — check that provided information is reasonable (e.g., vehicle year 
is not in the future, age is a valid number) 
4. Generate and present quote — compute a simple quote based on the collected 
data (the formula can be basic/dummy) and present it to the user 
5. Confirm or restart — let the user accept the quote, adjust details, or start over with 
a different product 
3. Requirements 
3.1 Must-Have Core 
6. LangGraph state machine orchestrator – routes between conversational and 
transactional modes based on detected user intent. The graph structure and state 
transitions should be clearly defined. 
7. Intent detection – classifies whether the user wants to ask a question about 
insurance (conversational) or get a quote (transactional), and routes accordingly.
8. RAG-powered – retrieves from your insurance knowledge base and generates 
grounded answers. Doesnʼt need to be fancy — a simple vector store with your 
insurance documents is fine. 
9. Quotation flow – clear step-by-step progression (identify product → collect details 
→ validate → generate quote → confirm), with input validation at each step. 
10. Graceful transitions – bot should handle a user switching intent mid-conversation 
(e.g., asking a product question while in the middle of a quotation flow) without 
crashing or losing collected data. 
3.2 Performance & Frontend Bonus 
We evaluate whether your chatbot feels fast and polished — not just functional. 
A. Latency Optimization 
Minimize perceived wait time. Optimize your chatbot for low latency without sacrificing 
response accuracy. 
B. Frontend & Chat Experience 
Build a web-based chat UI that feels like a real product — clear message bubbles, smooth scroll, loading states. Bonus: package it as an embeddable widget (iframe, web 
component, or script tag) with a short integration snippet showing how to drop it into any website. 
4. Knowledge Base 
Create a small knowledge base 510 documents or text chunks) about Ivory 
Insurance. This can be as simple as markdown or text files covering: 
• Company overview and available products (auto, home, life) 
• Coverage details for each product type (whatʼs included, whatʼs excluded) 
• Pricing tiers or coverage levels (e.g., basic, standard, comprehensive) 
• Claims process and policies (deductibles, filing deadlines, etc.) 
• FAQs (eligibility, cancellation policy, bundling discounts, etc.)
The content can be fictional. Include these documents in your repository. 
5. Technical Guidance 
You are free to choose your own tools and providers. Some suggestions: 
• Framework: LangGraph (required) 
• LLM Any model accessible via OpenRouter 
• Vector store: any 
• Embeddings: any 
• Interface: web application / widget (if possible) 
We highly encourage the use of AI coding assistants. We expect most candidates will. 
5.1 Provided API Key 
We will provide you with an OpenRouter API key with a $10 credit limit for this 
assessment. Use this key for all LLM and embedding API calls. 
6. Follow-Up Interview 
After reviewing your submission, we will schedule a follow-up interview where you will be asked to: 
● Present your solution — walk us through your architecture, state machine design, 
and key decisions 
● Demo your bot live and handle test scenarios we throw at it 
● Answer questions about your code/design