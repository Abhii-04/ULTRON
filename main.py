import asyncio
import faulthandler

from langgraph.types import Command

from src.agent import Agent
from src.config.terminal_ui import TerminalUI

faulthandler.enable(all_threads=True)


async def main():
    ui = TerminalUI()
    ui.show_boot()
    ui.show_setup()

    agent = Agent()
    await agent.setup()
    ui.show_ready()
    pending_interrupt = None

    try:
        while True:
            if pending_interrupt is not None:
                user_input = ui.ask_interrupt(pending_interrupt)
            else:
                user_input = ui.ask()

            if user_input.lower() in {"exit", "quit"}:
                break

            if pending_interrupt is not None:
                if isinstance(pending_interrupt, dict) and "awaiting" in pending_interrupt:
                    resume_value = {
                        "approved": user_input.strip().lower() in {"approve", "approved", "yes", "y"}
                    }
                else:
                    resume_value = user_input

                result = await ui.run_agent_turn(agent, Command(resume=resume_value))
            else:
                result = await ui.run_agent_turn(agent, user_input)

            pending_interrupt = None
            if "__interrupt__" in result:
                pending_interrupt = result["__interrupt__"][-1].value

    except (EOFError, KeyboardInterrupt):
        pass
    except Exception as error:
        ui.show_error(error)
        raise
    finally:
        await agent.close()
        ui.show_shutdown()


if __name__ == "__main__":
    asyncio.run(main())
