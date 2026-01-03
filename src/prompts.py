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
     "You are a STRICT relevance judge for government scheme retrieval.\n"
     "Given a user query and retrieved schemes with their content previews and similarity scores, "
     "judge if the schemes can answer the user's SPECIFIC question.\n\n"
     "Return YES (schemes are relevant) ONLY if:\n"
     "- Schemes directly address the query topic\n"
     "- Content preview shows relevant information\n"
     "- At least one scheme has high similarity score (>0.6)\n"
     "- Sufficient details present to answer the question\n\n"
     "Return NO (needs better retrieval) if:\n"
     "- Schemes don't match the query topic\n"
     "- Content is too generic or tangentially related\n"
     "- All similarity scores are low (<0.6)\n"
     "- Missing critical information to answer the question\n"
     "- Only scheme names match but content doesn't\n\n"
     "Be STRICT. When in doubt, return NO to trigger better retrieval.\n"
     "Respond ONLY with YES or NO."),
    ("human", "Query: {query}\n\nRetrieved Schemes:\n{schemes}")
])

reflection_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are a query refinement agent. The original query did not retrieve sufficiently "
     "relevant government schemes. Rewrite the query to be more precise, specific, and "
     "retrieval-friendly.\n\n"
     "Techniques:\n"
     "- Add specific keywords (eligibility, benefits, procedure, subsidy, etc.)\n"
     "- Expand abbreviations (PMEGP -> Prime Minister Employment Generation Programme)\n"
     "- Add context (manufacturing, women, youth, startup, MSME, etc.)\n"
     "- Make implicit details explicit\n\n"
     "Return ONLY the rewritten query, nothing else."),
    ("human", "Original Query: {query}")
])

answer_quality_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are a STRICT answer quality judge for government scheme queries.\n"
     "Judge if the answer DIRECTLY and COMPLETELY addresses the user's query.\n\n"
     "Return YES (answer is INADEQUATE and needs correction) if:\n"
     "- Answer is vague, indirect, or evasive\n"
     "- Uses phrases like 'no specific exclusion' instead of clear YES/NO\n"
     "- Doesn't directly answer the specific question asked\n"
     "- Missing critical details (amounts, percentages, age limits, etc.)\n"
     "- Says 'may be eligible' when documents have clear criteria\n"
     "- Too generic when specific information is requested\n"
     "- Answers a different question than what was asked\n\n"
     "Return NO (answer is GOOD) ONLY if:\n"
     "- Directly answers the exact question asked\n"
     "- Provides concrete, specific details\n"
     "- Clear and unambiguous\n"
     "- Includes relevant numbers, criteria, or procedures when asked\n\n"
     "Examples:\n"
     "Query: 'Can women apply for PMEGP?'\n"
     "BAD (return YES): 'There is no specific exclusion of women...' ← Evasive\n"
     "GOOD (return NO): 'Yes, women can apply for PMEGP. The scheme is open to all...' ← Direct\n\n"
     "Be STRICT. When in doubt, return YES to trigger answer improvement.\n"
     "Respond ONLY with YES or NO."),
    ("human", "Query: {query}\n\nAnswer: {answer}")
])

corrective_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "The answer to the user query was inadequate or incomplete. "
     "Rewrite the query to retrieve better documents that can answer the question more directly.\n\n"
     "Strategies:\n"
     "- Add missing keywords from the original question\n"
     "- Be more specific about what information is needed\n"
     "- Focus on the exact aspect being asked (eligibility, benefits, procedure, etc.)\n"
     "- Include synonyms or related terms\n\n"
     "Return ONLY the improved query."),
    ("human", "Original Query: {query}")
])

answer_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are a government schemes expert for Indian citizens.\n"
     "Answer the user's question DIRECTLY and SPECIFICALLY using ONLY the provided schemes.\n\n"
     "Guidelines:\n"
     "- Start with a direct answer to the exact question asked\n"
     "- Use concrete details (amounts, percentages, eligibility criteria)\n"
     "- Quote specific schemes by name\n"
     "- For yes/no questions, start with 'Yes' or 'No' clearly\n"
     "- Include relevant URLs for more information\n"
     "- If information is missing from documents, state it clearly\n"
     "- Do NOT hallucinate or make assumptions\n"
     "- Prioritize information from higher relevance score documents\n\n"
     "Format:\n"
     "- Use bullet points for lists\n"
     "- Bold scheme names using **Scheme Name**\n"
     "- Keep answers concise but complete"),
    ("human", "Query: {query}\n\nRelevant Government Schemes:\n{schemes}")
])
