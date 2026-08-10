import asyncio

from app.services.email import send_email


async def test():
    await send_email(
        to_email="sujalgoyal70@gmail.com",
        subject="FlowPilot SMTP Test",
        body=(
            "Hello!\n\n"
            "This is a test email from FlowPilot.\n\n"
            "If you received this email, "
            "Gmail SMTP is working correctly."
        ),
    )

    print("Email sent successfully!")


if __name__ == "__main__":
    asyncio.run(test())