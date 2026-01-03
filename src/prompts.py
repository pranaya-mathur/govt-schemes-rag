from langchain_core.prompts import ChatPromptTemplate
import config


intent_prompt = ChatPromptTemplate.from_messages([
    ("system", 
     f"You are an intent classifier for government scheme queries. "
     f"Classify the user query into ONE of the following labels only: {config.INTENT_LABELS}\n"
     f"Return ONLY the label, nothing else."),
    ("human", "{query}")
])

relevance_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are a relevance judge for government scheme retrieval.\n"
     "Given a user query and retrieved schemes, decide if the schemes are relevant.\n\n"
     "Return YES if the schemes can help answer the query.\n"
     "Return NO if the schemes are off-topic or unhelpful.\n\n"
     "Be reasonable - docs don't need to be perfect, just useful.\n\n"
     "Respond ONLY with YES or NO."),
    ("human", "Query: {query}\n\nRetrieved Schemes:\n{schemes}")
])

reflection_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are a query refinement agent. The original query did not retrieve relevant schemes.\n"
     "Rewrite the query to be more specific and retrieval-friendly.\n\n"
     "Techniques:\n"
     "- Add specific keywords (eligibility, benefits, procedure, subsidy)\n"
     "- Expand abbreviations\n"
     "- Add context (manufacturing, women, youth, startup, MSME)\n\n"
     "Return ONLY the rewritten query."),
    ("human", "Original Query: {query}")
])

answer_quality_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are an answer quality judge.\n"
     "Judge if the answer adequately addresses the user's query.\n\n"
     "Return YES if the answer is INADEQUATE (completely off-topic, wrong, or unhelpful).\n"
     "Return NO if the answer is ADEQUATE (on-topic, helpful, and addresses the question).\n\n"
     "Don't demand perfection - good enough is acceptable.\n\n"
     "Respond ONLY with YES or NO."),
    ("human", "Query: {query}\n\nAnswer: {answer}")
])

corrective_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "The answer was inadequate. Rewrite the query to retrieve better documents.\n\n"
     "Strategies:\n"
     "- Add missing keywords from the question\n"
     "- Be more specific about what information is needed\n"
     "- Include synonyms or related terms\n\n"
     "Return ONLY the improved query."),
    ("human", "Original Query: {query}")
])

answer_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are a government schemes expert for Indian citizens.\n"
     "Answer the user's question using ONLY the provided schemes.\n\n"
     "Guidelines:\n"
     "- Start with a direct answer\n"
     "- Use concrete details (amounts, eligibility criteria)\n"
     "- Quote specific schemes by name\n"
     "- For yes/no questions, start with 'Yes' or 'No'\n"
     "- Include relevant URLs\n"
     "- If information is missing, state it clearly\n"
     "- Do NOT make assumptions\n\n"
     "Format:\n"
     "- Use bullet points for lists\n"
     "- Bold scheme names using **Scheme Name**"),
    ("human", "Query: {query}\n\nGovernment Schemes:\n{schemes}")
])
