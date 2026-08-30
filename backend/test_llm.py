import asyncio

from app.services.llm_service import LLMService


async def main():
    llm_service = LLMService()

    response = await llm_service.invoke(
        "Explain in one sentence what an employee onboarding workflow is."
    )

    print(response)


if __name__ == "__main__":
    asyncio.run(main())
    