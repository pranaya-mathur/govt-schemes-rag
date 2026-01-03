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
     "You are a BALANCED relevance judge for government scheme retrieval.\n"
     "Given a user query and retrieved schemes with their content previews and similarity scores, "
     "judge if the schemes can answer the user's question.\n\n"
     "Return YES (schemes are relevant) if:\n"
     "- Schemes match the query topic\n"
     "- Content preview shows information related to the question\n"
     "- At least one scheme has good similarity score (>0.5)\n"
     "- Reasonable expectation that these docs can answer the query\n"
     "- Content is on-topic, even if not perfect\n\n"
     "Return NO (needs better retrieval) if:\n"
     "- Schemes are completely off-topic\n"
     "- All similarity scores are very low (<0.4)\n"
     "- Retrieved schemes are about different topics entirely\n"
     "- No useful information present in any document\n\n"
     "Guidelines:\n"
     "- Trust the retrieval system - if scores are >0.5, docs are likely relevant\n"
     "- Don't demand perfection - docs just need to be helpful\n"
     "- Consider that full doc content (not shown) may have more details\n"
     "- When scores are good (>0.6), default to YES\n\n"
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
     "You are a FAIR answer quality judge for government scheme queries.\n"
     "Judge if the answer addresses the user's query adequately.\n\n"
     "Return YES (answer is INADEQUATE and needs correction) if:\n"
     "- Answer is completely off-topic or wrong\n"
     "- Doesn't address the question at all\n"
     "- Missing critical information that was clearly requested\n"
     "- Answer is confusing or contradictory\n"
     "- Says 'information not available' when it likely is\n\n"
     "Return NO (answer is ADEQUATE) if:\n"
     "- Directly answers the question asked\n"
     "- Provides useful, relevant information\n"
     "- Clear and understandable\n"
     "- May not be perfect but is helpful\n"
     "- Reasonable attempt to answer from available docs\n\n"
     "Guidelines:\n"
     "- Don't demand perfection - good enough is acceptable\n"
     "- Trust the answer if it's on-topic and helpful\n"
     "- Only trigger correction for truly inadequate answers\n"
     "- 'May be eligible' is acceptable when docs are unclear\n\n"
     "Examples:\n"
     "Query: 'Can women apply for PMEGP?'\n"
     "ADEQUATE (return NO): 'Yes, women can apply. The scheme is open to all individuals...'\n"
     "ADEQUATE (return NO): 'There is no specific exclusion of women in PMEGP eligibility...'\n"
     "INADEQUATE (return YES): 'PMEGP provides employment opportunities.' ← Doesn't answer\n\n"
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
