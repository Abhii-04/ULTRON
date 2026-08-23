import asyncio
import faulthandler

from src.agent import Agent

faulthandler.enable(all_threads=True)


async def main():
    agent = Agent()
    await agent.setup()

    try:
        while True:
            user_input = input("You: ")

            if user_input.lower() in {"exit", "quit"}:
                break

            await agent.run_superstep(user_input, [])

    finally:
        await agent.close()


if __name__ == "__main__":
    asyncio.run(main())
