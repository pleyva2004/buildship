"""Stage 1 adapters — concrete implementations of the four ``buildship_core`` Protocols.

These are the ONLY modules that import Nebius (via the OpenAI-compatible SDK),
Composio, or Tavily. The core (``buildship/buildship_core.py``) stays vendor-free
and is not modified.

Verified against the installed SDKs (2026-06): openai 2.41.0, tavily-python
0.7.25, composio 0.13.1 / composio_client 1.39.0.

Every adapter reads its secrets from environment variables (see ``.env.example``).
No secrets are hardcoded. Construct an adapter only after ``load_dotenv()`` has run.

Two spots in :class:`ComposioSandbox` are backend-defined and could not be
verified from the SDK source — they are configurable via env and flagged inline:
  * the COMPOSIO_REMOTE_WORKBENCH *argument key* (``BUILDSHIP_WORKBENCH_ARG``), and
  * how to read stdout / pass-fail out of the response ``data`` dict.
If your first live run errors at the sandbox step, those are the knobs to turn —
or set ``BUILDSHIP_SANDBOX=local`` to validate the rest of the loop first.
"""

from __future__ import annotations

import ast
import inspect
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

from buildship.buildship_core import Harness, ToolContract, ToolRegistry

# The dataset the hero task charts. The generated tool follows the calling
# convention ``def NAME(data: dict, out_path: str) -> str`` so the Action can
# materialize the artifact in-process before firing the real Composio action.
SAMPLE_DATA: dict[str, int] = {"Mon": 12, "Tue": 19, "Wed": 7, "Thu": 23, "Fri": 15}


# ===========================================================================
# Helpers
# ===========================================================================
def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"{name} is not set. Copy .env.example to .env and fill it in."
        )
    return value


def _parse_tool_json(content: str) -> dict[str, Any]:
    """Parse the model's JSON response into a dict, tolerating markdown fences."""
    text = (content or "").strip()
    if text.startswith("```"):
        # strip a leading ```json / ``` fence and the trailing ```
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.rstrip().endswith("```"):
            text = text.rsplit("```", 1)[0]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError(f"LLM response was not JSON:\n{content[:500]}")
        return json.loads(text[start : end + 1])


def _align_tool_name(declared: str, code: str) -> str:
    """Reconcile the registry key with the actual top-level def in ``code``.

    The core materializes a tool via ``exec(code, ns); ns[name]``, so the
    registry key MUST equal the function's def name or the tool raises KeyError
    at the action step (after it already passed its sandbox self-test). If the
    declared name doesn't match a top-level def but there's exactly one, defer to
    the real def name; otherwise keep the declared name and let the sandbox catch it.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return declared  # the sandbox self-test will surface the syntax error
    funcs = [
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    if declared in funcs:
        return declared
    if len(funcs) == 1:
        return funcs[0]
    return declared


# ===========================================================================
# (5a) LLMClient — Nebius codegen via the OpenAI-compatible SDK
# ===========================================================================
_CODEGEN_SYSTEM = """You are a Python tool-writing engine for the buildship harness.
Given a TASK the agent cannot yet do (plus optional research notes and feedback from
a prior failed attempt), you write ONE small, self-contained Python tool.

Respond with ONLY a single JSON object (no markdown, no prose) with EXACTLY these keys:
  - "name":      snake_case function name; this is also the registry key.
  - "signature": the def line, e.g. "def make_bar_chart(data: dict, out_path: str) -> str:".
  - "docstring": what the tool does, its args, and what it returns.
  - "code":      the FULL python source of the function, including every import it needs
                 and the complete def. It must be runnable as-is.
  - "self_test": python that exercises the function and PROVES it works. It is appended
                 to "code" in the SAME module, so call the function by its name directly.
                 It must build its own small sample data, call the function with a
                 temp output path (use tempfile), assert the result file exists and is
                 non-empty, and finally print exactly "SELF_TEST_OK".
  - "requires":  list of pip package names the code imports, e.g. ["matplotlib"].

Hard rules (the tool is REJECTED unless ALL hold):
  1. CALLING CONVENTION: the function MUST accept exactly (data: dict, out_path: str)
     and MUST return out_path (the path to the artifact it wrote).
  2. For charts use matplotlib with a NON-interactive backend: put
     `import matplotlib` then `matplotlib.use("Agg")` BEFORE importing pyplot.
     Save the figure to out_path with plt.savefig(out_path); never call plt.show().
  3. Keep it small, deterministic, and dependency-light.
  4. If feedback describes a previous failure, FIX that specific error; do not repeat it.
"""


class NebiusLLMClient:
    """LLMClient: generate a ToolContract via Nebius (OpenAI-compatible) codegen.

    Uses a strong coder model at low temperature and asks for strict JSON. The
    ``feedback`` arg (prior traceback + rejected-attempt count) is forwarded so
    the model can self-correct on retries.
    """

    def __init__(
        self,
        model: str | None = None,
        temperature: float | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        from openai import OpenAI

        self.model = model or os.environ.get("NEBIUS_MODEL", "deepseek-ai/DeepSeek-V3")
        self.temperature = float(
            temperature
            if temperature is not None
            else os.environ.get("BUILDSHIP_CODEGEN_TEMPERATURE", "0.1")
        )
        self._client = OpenAI(
            api_key=api_key or _require("NEBIUS_API_KEY"),
            base_url=base_url
            or os.environ.get("NEBIUS_BASE_URL", "https://api.studio.nebius.ai/v1"),
        )

    def write_tool(
        self, task: str, research: str, feedback: str, current_tools: list[str]
    ) -> ToolContract:
        user = self._build_prompt(task, research, feedback, current_tools)
        response = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": _CODEGEN_SYSTEM},
                {"role": "user", "content": user},
            ],
            temperature=self.temperature,
            response_format={"type": "json_object"},
        )
        data = _parse_tool_json(response.choices[0].message.content or "")
        code = data["code"]
        return ToolContract(
            name=_align_tool_name(data["name"], code),
            signature=data["signature"],
            docstring=data["docstring"],
            code=code,
            self_test=data["self_test"],
            requires=list(data.get("requires") or []),
        )

    @staticmethod
    def _build_prompt(
        task: str, research: str, feedback: str, current_tools: list[str]
    ) -> str:
        parts = [f"TASK:\n{task}\n"]
        if current_tools:
            parts.append(f"Tools already in the library (do not rebuild): {current_tools}\n")
        if research:
            parts.append(f"RESEARCH NOTES (from web search):\n{research}\n")
        if feedback:
            parts.append(f"FEEDBACK FROM PRIOR ATTEMPT (fix this, do not repeat it):\n{feedback}\n")
        parts.append("Return the JSON tool object now.")
        return "\n".join(parts)


# ===========================================================================
# (5b) Sandbox — Composio remote workbench (with a local subprocess fallback)
# ===========================================================================
_FAILURE_MARKERS = (
    "Traceback (most recent call last)",
    "AssertionError",
    "SyntaxError",
    "ModuleNotFoundError",
    "NameError",
)


def _coerce_output(data: dict[str, Any]) -> str:
    """Pull a human-readable combined stdout/stderr out of the workbench ``data``.

    The inner shape of ``data`` is backend-defined (not in the SDK), so we try the
    common keys and fall back to the raw JSON.
    """
    if not isinstance(data, dict):
        return str(data)
    chunks = []
    for key in ("output", "stdout", "logs", "result", "stderr", "error"):
        val = data.get(key)
        if val:
            chunks.append(str(val))
    return "\n".join(chunks) if chunks else json.dumps(data)[:2000]


def _looks_passed(output: str, data: dict[str, Any]) -> bool:
    exit_code = data.get("exit_code") if isinstance(data, dict) else None
    if exit_code is not None:
        return int(exit_code) == 0
    if "SELF_TEST_OK" in output:
        return True
    return not any(marker in output for marker in _FAILURE_MARKERS)


class ComposioSandbox:
    """Sandbox: run a tool's source (function + self-test) in Composio's remote workbench.

    Creates a tool-router session with the workbench enabled, then executes the
    COMPOSIO_REMOTE_WORKBENCH meta tool with the source. Returns
    ``(passed, combined_stdout_stderr)``.
    """

    def __init__(
        self,
        user_id: str | None = None,
        sandbox_size: str | None = None,
        arg_key: str | None = None,
        api_key: str | None = None,
    ) -> None:
        from composio import Composio

        self._composio = Composio(api_key=api_key or _require("COMPOSIO_API_KEY"))
        self.user_id = user_id or os.environ.get("COMPOSIO_USER_ID", "buildship")
        self.sandbox_size = sandbox_size or os.environ.get(
            "BUILDSHIP_SANDBOX_SIZE", "standard"
        )
        # Backend-defined arg key for the workbench source — config, not verified.
        self.arg_key = arg_key or os.environ.get("BUILDSHIP_WORKBENCH_ARG", "code")
        self._session: Any = None

    def _ensure_session(self) -> Any:
        if self._session is None:
            self._session = self._composio.tool_router.create(
                user_id=self.user_id,
                workbench={"enable": True, "sandbox_size": self.sandbox_size},
            )
        return self._session

    def run(self, source: str) -> tuple[bool, str]:
        session = self._ensure_session()
        response = self._composio.client.tool_router.session.execute_meta(
            session_id=session.session_id,
            slug="COMPOSIO_REMOTE_WORKBENCH",
            arguments={self.arg_key: source},
        )
        data = response.data if isinstance(response.data, dict) else {}
        output = _coerce_output(data)
        passed = response.error is None and _looks_passed(output, data)
        if response.error:
            output = f"{output}\n[composio error] {response.error}".strip()
        return passed, output


class LocalSandbox:
    """Sandbox fallback: run the source in a subprocess with the current interpreter.

    Selected via ``BUILDSHIP_SANDBOX=local``. Useful to validate the full loop
    before the Composio remote workbench is wired up. Not isolated — only run
    code you are willing to execute locally (the demo's generated tools are).
    """

    def __init__(self, timeout: int | None = None) -> None:
        self.timeout = int(timeout or os.environ.get("BUILDSHIP_SANDBOX_TIMEOUT", "60"))

    def run(self, source: str) -> tuple[bool, str]:
        with tempfile.NamedTemporaryFile(
            "w", suffix=".py", delete=False, encoding="utf-8"
        ) as handle:
            handle.write(source)
            path = handle.name
        try:
            proc = subprocess.run(
                [sys.executable, path],
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            output = ((proc.stdout or "") + (proc.stderr or "")).strip()
            return proc.returncode == 0, output
        except subprocess.TimeoutExpired as exc:
            tail = (exc.stdout or "") + (exc.stderr or "")
            return False, f"TimeoutExpired after {self.timeout}s\n{tail}"
        finally:
            os.unlink(path)


# ===========================================================================
# (5c) Searcher — Tavily web/API-docs search
# ===========================================================================
class TavilySearcher:
    """Searcher: fetch an API/usage-docs snippet via Tavily."""

    def __init__(self, api_key: str | None = None, max_results: int | None = None) -> None:
        from tavily import TavilyClient

        self._client = TavilyClient(api_key=api_key or _require("TAVILY_API_KEY"))
        self.max_results = int(
            max_results or os.environ.get("BUILDSHIP_SEARCH_MAX_RESULTS", "5")
        )

    def search(self, query: str) -> str:
        response = self._client.search(
            query=query,
            search_depth="basic",
            max_results=self.max_results,
            include_answer=True,
        )
        answer = response.get("answer") or ""
        snippets = "\n".join(
            r.get("content", "") for r in (response.get("results") or [])[:3]
        )
        return f"{answer}\n\n{snippets}".strip()


# ===========================================================================
# (5d) Action — fire a real Composio action (post the chart to Slack)
# ===========================================================================
class ComposioAction:
    """Action: materialize the freshly-built chart tool, then post it via Composio.

    Step 1 renders the chart in-process by calling the validated tool with
    SAMPLE_DATA (the convention is ``tool(data: dict, out_path: str) -> path``).
    Step 2 fires a real Composio action (default: post a Slack message; set
    ``BUILDSHIP_ACTION_FILE_ARG`` to also attach the PNG via a file-upload action).

    Account/connection setup is deployment-specific: connect Slack in Composio
    and set the action slug, channel, and (optionally) connected-account id via env.
    """

    def __init__(self) -> None:
        from composio import Composio

        self.artifact_dir = Path(
            os.environ.get("BUILDSHIP_ARTIFACT_DIR", "artifacts")
        ).resolve()
        self.artifact_dir.mkdir(parents=True, exist_ok=True)

        # Auto file upload is gated behind these flags + an allowlisted dir.
        self._composio = Composio(
            api_key=_require("COMPOSIO_API_KEY"),
            dangerously_allow_auto_upload_download_files=True,
            file_upload_dirs=[str(self.artifact_dir)],
        )
        self.user_id = os.environ.get("COMPOSIO_USER_ID", "buildship")
        self.connected_account_id = (
            os.environ.get("COMPOSIO_CONNECTED_ACCOUNT_ID") or None
        )
        self.slug = os.environ.get(
            "BUILDSHIP_ACTION_SLUG", "SLACK_SENDS_A_MESSAGE_TO_A_CHANNEL"
        )
        self.channel = os.environ.get("BUILDSHIP_SLACK_CHANNEL", "")
        self.channel_arg = os.environ.get("BUILDSHIP_ACTION_CHANNEL_ARG", "channel")
        self.text_arg = os.environ.get("BUILDSHIP_ACTION_TEXT_ARG", "text")
        # Empty by default => text-only message (reliably fires). Set to the action's
        # file-argument key (e.g. "file") to also upload the PNG.
        self.file_arg = os.environ.get("BUILDSHIP_ACTION_FILE_ARG", "")

    def execute(self, tool_name: str, tool: Callable[..., Any]) -> str:
        out_path = str(self.artifact_dir / f"{tool_name}.png")
        produced = self._render(tool, out_path)

        arguments: dict[str, Any] = {
            self.text_arg: f"buildship built and ran `{tool_name}` — chart at {produced}"
        }
        if self.channel:
            arguments[self.channel_arg] = self.channel
        if self.file_arg:
            arguments[self.file_arg] = produced

        response = self._composio.tools.execute(
            self.slug,
            arguments,
            connected_account_id=self.connected_account_id,
            user_id=self.user_id,
            dangerously_skip_version_check=True,
        )
        successful = response.get("successful")
        detail = json.dumps(response.get("data"))[:300]
        return (
            f"action={self.slug} successful={successful} artifact={produced} "
            f"data={detail}"
        )

    @staticmethod
    def _render(tool: Callable[..., Any], out_path: str) -> str:
        """Call the built tool to write the chart, honoring the (data, out_path) convention."""
        try:
            param_count = len(inspect.signature(tool).parameters)
        except (TypeError, ValueError):
            param_count = 2

        if param_count >= 2:
            result = tool(SAMPLE_DATA, out_path)
        elif param_count == 1:
            result = tool(SAMPLE_DATA)
        else:
            result = tool()

        produced = result if isinstance(result, str) and result else out_path
        if not Path(produced).exists() or Path(produced).stat().st_size == 0:
            raise RuntimeError(
                f"tool ran but produced no artifact at {produced!r}"
            )
        return produced


# ===========================================================================
# Factory / wiring helpers
# ===========================================================================
def make_sandbox():
    """Return the sandbox adapter selected by ``BUILDSHIP_SANDBOX`` (composio|local)."""
    backend = os.environ.get("BUILDSHIP_SANDBOX", "composio").lower()
    if backend == "local":
        return LocalSandbox()
    return ComposioSandbox()


def build_harness(registry_path: str | None = None) -> Harness:
    """Wire the four adapters into a core ``Harness`` ready to run a task."""
    registry = ToolRegistry(
        registry_path or os.environ.get("BUILDSHIP_LIBRARY", "buildship_library.json")
    )
    return Harness(
        llm=NebiusLLMClient(),
        sandbox=make_sandbox(),
        searcher=TavilySearcher(),
        action=ComposioAction(),
        registry=registry,
    )
