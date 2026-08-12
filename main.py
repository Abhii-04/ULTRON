import asyncio
import faulthandler
from src.agent import Agent   # your file name

faulthandler.enable(all_threads=True)

async def main():
    agent = Agent()

    await agent.setup()

    while True:
        user_input = input("You: ")

        if user_input.lower() in {"exit", "quit"}:
            break

        await agent.run_superstep(user_input, [])

asyncio.run(main())
