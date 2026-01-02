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
     "You are a strict relevance judge. Given a user query and retrieved government schemes, "
     "decide if the retrieved schemes are sufficient and relevant to answer the query. "
     "Respond ONLY with YES or NO."),
    ("human", "Query: {query}\nSchemes: {schemes}")
])

reflection_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are a query refinement agent. The original query did not retrieve sufficiently "
     "relevant government schemes. Rewrite the query to be more precise, specific, and "
     "retrieval-friendly. Return ONLY the rewritten query, nothing else."),
    ("human", "Original Query: {query}")
])

answer_quality_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are a strict answer quality judge. Given a user query and an answer, decide if "
     "the answer is incomplete, vague, or does not directly address the query. "
     "Respond ONLY with YES or NO."),
    ("human", "Query: {query}\nAnswer: {answer}")
])

corrective_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "The answer to the user query was inadequate. Rewrite the query to improve document "
     "retrieval so a better answer can be generated. Return ONLY the improved query."),
    ("human", "Original Query: {query}")
])

answer_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are a government schemes expert. Answer the user's question strictly using the "
     "provided schemes. If information is missing, say so clearly. Do NOT hallucinate."),
    ("human", "Query: {query}\n\nSchemes:\n{schemes}")
])
