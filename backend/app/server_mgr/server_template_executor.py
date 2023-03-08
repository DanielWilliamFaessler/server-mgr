from dataclasses import dataclass
import subprocess


@dataclass
class ShellExecutionResult:
    result: str = None
    success: bool = False
    error: str = None
    reason: str = None


def run(command: str) -> ShellExecutionResult:
    # stop command after 10 Minutes
    TIMEOUT_SECONDS = 60 * 10
    result = subprocess.run(command, text=True, shell=True, capture_output=True, timeout=TIMEOUT_SECONDS)
    reason = None
    try:
        result.check_returncode()
    except subprocess.CalledProcessError as e:
        reason = f"{e}"
    success = False
    if result.returncode == 0:
        success = True
    msg = ShellExecutionResult(success=success, result=result.stdout, error=result.stderr, reason=reason)
    return msg
