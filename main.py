import asyncio
import faulthandler

from langgraph.types import Command

from src.agent import Agent

faulthandler.enable(all_threads=True)


async def main():
    agent = Agent()
    await agent.setup()
    pending_interrupt = None

    try:
        while True:
            user_input = input("You: ")

            if user_input.lower() in {"exit", "quit"}:
                break

            if pending_interrupt is not None:
                if isinstance(pending_interrupt, dict) and "awaiting" in pending_interrupt:
                    resume_value = {
                        "approved": user_input.strip().lower() in {"approve", "approved", "yes", "y"}
                    }
                else:
                    resume_value = user_input

                result = await agent.run_superstep(Command(resume=resume_value), [])
            else:
                result = await agent.run_superstep(user_input, [])

            pending_interrupt = None
            if "__interrupt__" in result:
                pending_interrupt = result["__interrupt__"][-1].value

    finally:
        await agent.close()


if __name__ == "__main__":
    asyncio.run(main())
