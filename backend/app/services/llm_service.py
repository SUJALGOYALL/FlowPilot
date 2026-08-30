from langchain_groq import ChatGroq

from app.core.config import settings


class LLMService:
    def __init__(self):
        if not settings.GROQ_API_KEY:
            raise ValueError(
                "GROQ_API_KEY is not configured."
            )

        if not settings.GROQ_MODEL:
            raise ValueError(
                "GROQ_MODEL is not configured."
            )

        self.llm = ChatGroq(
            api_key=settings.GROQ_API_KEY,
            model=settings.GROQ_MODEL,
            temperature=0,
        )

    async def invoke(
        self,
        prompt: str,
    ) -> str:
        response = await self.llm.ainvoke(prompt)

        return response.content