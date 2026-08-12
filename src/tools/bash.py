import subprocess 
from langchain_core import outputs
from langchain_core.tools import tool
import pathlib


PROJECT_ROOT = (pathlib.Path.cwd().resolve)

def safe_path_for_project(path:str)->pathlib.Path:
    """Resolve a relative path and ensure it stays inside the project root."""
    if not isinstance(path,str):
        raise TypeError("path must be a string")

    #Empty path means proejct root
    if not path:
        path="."
    requested_path= pathlib.Path(path)

    #Absolute path are not allowed
    if requested_path.is_absolute():
        raise ValueError(
            "Absolute path are not allowed",
            "use a path relative to the proejct url"
        )
    #Resolve the path aganist the project root
    resolved_path=(PROJECT_ROOT/requested_path).resolve()

    #make sure the resolved path is still inside project_root
    try:
        resolved_path.relative_to(PROJECT_ROOT)
    except ValueError:
        raise ValueError(
            f"Path {path} is outside the porject root",
            f"Use a path relative to the {PROJECT_ROOT}."
        )

    return resolved_path




@tool
def bash(path:str,command:str)->str:
    """Run a shell command for a project directory and return stdout/stderr."""
    p=safe_path_for_project(path)
    if not p.exists():
        return f"ERROR: {path} does not exist"

    if not p.is_dir():
        return f"ERROR: {path} is not a directory"
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
    
