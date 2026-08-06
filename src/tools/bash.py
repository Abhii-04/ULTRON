import subprocess 
from langchain_core import outputs
from langchain_core.tools import tool

@tool
def bash(command:str)->str:
    """Execute a bash command and return stdout/stderr """

    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        timeout=60,
        
    )

    output=" "
    if result.stdout:
        output+=f"STDOUT:\n{result.stdout}"
    if result.stderr:
        output += f"STDERR:\n{result.stderr}"

    print("ran bash tool")

    return output
    