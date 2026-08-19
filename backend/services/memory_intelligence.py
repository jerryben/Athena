import json
import re

from loguru import logger
from openai import OpenAI

from backend.core.config import settings


class MemoryIntelligence:
    """
    Determines whether a user's message contains information
    that should become long-term memory.

    This service ONLY identifies memory candidates.

    It does NOT:
        - decide whether a candidate is new
        - decide whether a candidate should update existing memory
        - search Qdrant
        - delete memories
        - write memories

    Those responsibilities belong to the memory service /
    memory considerator layer.
    """

    def __init__(self):
        self.client = OpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
        )

    # ============================================================
    # JSON EXTRACTION
    # ============================================================

    def _extract_json(self, text: str) -> dict | None:
        """
        Safely extract the first JSON object returned by the LLM.

        Handles:
            - normal JSON
            - JSON inside ```json blocks
            - extra text surrounding JSON
            - accidental multiple JSON objects

        Returns:
            dict or None
        """

        if not text:
            return None

        text = text.strip()

        # --------------------------------------------------------
        # Remove markdown code fences
        # --------------------------------------------------------

        text = re.sub(
            r"```json\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )

        text = re.sub(
            r"```\s*",
            "",
            text,
        )

        text = text.strip()

        # --------------------------------------------------------
        # Try complete JSON first
        # --------------------------------------------------------

        try:
            result = json.loads(text)

            if isinstance(result, dict):
                return result

        except json.JSONDecodeError:
            pass

        # --------------------------------------------------------
        # Find first JSON object
        # --------------------------------------------------------

        start = text.find("{")

        if start == -1:
            return None

        depth = 0
        in_string = False
        escape = False

        for index in range(start, len(text)):
            char = text[index]

            # ----------------------------------------------------
            # Track JSON strings
            # ----------------------------------------------------

            if char == '"' and not escape:
                in_string = not in_string

            if char == "\\" and not escape:
                escape = True
                continue

            escape = False

            if in_string:
                continue

            # ----------------------------------------------------
            # Track JSON object depth
            # ----------------------------------------------------

            if char == "{":
                depth += 1

            elif char == "}":
                depth -= 1

                if depth == 0:

                    candidate = text[start : index + 1]

                    try:
                        result = json.loads(candidate)

                        if isinstance(result, dict):
                            return result

                    except json.JSONDecodeError:
                        return None

        return None

    # ============================================================
    # MEMORY INTELLIGENCE
    # ============================================================

    def should_save(
        self,
        user_message: str,
    ):
        """
        Determine whether the USER MESSAGE contains information
        worth storing as long-term memory.

        The USER MESSAGE is the sole source of memory candidates.

        This service does not:
            - search existing memories
            - decide whether a candidate already exists
            - decide whether an existing memory should be updated
            - delete memories
            - write memories

        Those responsibilities belong to the memory
        considerator and memory service layers.
        """

        # ========================================================
        # SYSTEM PROMPT
        # ========================================================

        system_prompt = """

You are Athena's Long-Term Memory Intelligence.

Your ONLY responsibility is to determine whether the USER MESSAGE
contains information that should become long-term memory.

============================================================
SOURCE OF TRUTH
============================================================

The USER MESSAGE is the ONLY source of truth for memory extraction.

You do NOT receive or use:

- assistant responses
- existing memories
- Qdrant results
- conversation history
- model assumptions about Jerry

Information must not become a memory unless it is supported
by the USER MESSAGE itself.

============================================================
YOUR RESPONSIBILITY
============================================================

Your task is ONLY to:

1. Read the USER MESSAGE.
2. Determine whether it contains persistent information about Jerry.
3. If yes, return exactly ONE memory candidate.
4. If no, return:

{
    "save": false,
    "operation": "none"
}

============================================================
WHAT YOU MUST NOT DO
============================================================

You are NOT responsible for:

- searching existing memories
- deciding whether a memory already exists
- deciding whether an existing memory should be updated
- deciding whether a candidate is a duplicate
- resolving conflicts with existing memories
- deleting memories
- performing memory CRUD operations
- searching Qdrant
- comparing candidates with stored memories

The Memory Considerator and MemoryService handle those
responsibilities later.

============================================================
CRITICAL MEMORY EXTRACTION RULE
============================================================

NEVER create a memory from information that appears only in:

- an assistant response
- previous conversation history
- an existing memory
- Qdrant
- model knowledge
- assumptions
- inference unsupported by the USER MESSAGE

Only information explicitly supported by the current USER MESSAGE
may become a memory.

============================================================
MEMORY CANDIDATE RULE
============================================================

A memory candidate must describe persistent information about Jerry.

Save information that is likely to remain useful across future
conversations.


============================================================
CRITICAL SOURCE RULE
============================================================

ONLY the USER MESSAGE may create a memory.

The ASSISTANT RESPONSE is context only.

NEVER create a memory from information that appears only
in the assistant response.

For example:

USER:
"I want to become an AI engineer."

ASSISTANT:
"AI engineers use Python, PyTorch and TensorFlow..."

The memory may contain the user's goal:

"Jerry is working toward becoming an AI engineer."

But MUST NOT contain:

"Jerry uses PyTorch."

because that information came only from the assistant.

============================================================
WHAT SHOULD BE SAVED
============================================================

Save information that is likely to remain useful across
future conversations.

SAVE:

- Personal preferences
- Identity
- Career information
- Career goals
- Long-term goals
- Skills
- Technologies the user regularly uses
- Projects
- Long-term plans
- Professional interests
- Important relationships
- Recurring habits or workflows
- Strongly stated preferences
- Major changes to existing preferences
- Major changes to existing goals
- Major changes to existing projects

DO NOT SAVE:

- Greetings
- Small talk
- Jokes
- One-time questions
- Generic technical questions
- General explanations
- Temporary requests
- Information about products or technologies that the user
  merely asks about
- Information appearing only in the assistant response
- Generic facts that do not describe Jerry

============================================================
HARD RULE: EXPLICIT GOALS
============================================================

Explicit goals and career intentions are ALWAYS candidates.

Examples:

"I want to become an AI engineer."

"I am working toward becoming an AI engineer."

"My goal is to become an AI engineer."

"I am trying to transition into AI engineering."

"I want to move into cloud engineering."

"I plan to become a DevOps engineer."

"I want to learn Kubernetes."

"I am working toward becoming a machine learning engineer."

These MUST be classified as:

"operation": "candidate"

and:

"type": "goal"

Do NOT reject these as temporary statements.

============================================================
HARD RULE: EXPLICIT PREFERENCES
============================================================

Explicit personal preferences are candidates.

Examples:

"My favorite editor is VS Code."

"I prefer Neovim."

"I prefer Python."

"I like using Docker."

"I prefer Ubuntu."

These MUST normally be classified as:

"type": "preference"

============================================================
HARD RULE: CAREER / PROFESSIONAL IDENTITY
============================================================

Statements describing Jerry's current career, profession,
role or professional identity should normally be saved.

Examples:

"I am a Cloud Engineer."

"I work as a DevOps engineer."

"I am a network engineer."

"I work in IT."

"I am learning AI engineering."

These should normally become:

"type": "identity"

unless the statement is clearly a future goal, in which case
use:

"type": "goal"

============================================================
HARD RULE: SKILLS AND TECHNOLOGY USAGE
============================================================

Save skills or technologies when the USER indicates actual
experience, regular usage, ownership, or meaningful proficiency.

Examples:

"I use Docker extensively."

"I work with Kubernetes."

"I have experience with Terraform."

"Python is one of my main programming languages."

These can become:

"type": "fact"

Do NOT infer skills merely because the assistant mentions them.

============================================================
HARD RULE: QUESTIONS ARE NOT MEMORIES
============================================================

A question about a technology is NOT automatically a memory.

Example:

"What is the difference between Docker and Podman?"

DO NOT SAVE.

"How does Kubernetes work?"

DO NOT SAVE.

"Can you explain Terraform?"

DO NOT SAVE.

The fact that Jerry asks about Docker, Podman, Kubernetes,
or Terraform does NOT prove that he uses them.

============================================================
HARD RULE: TEMPORARY REQUESTS
============================================================

Do not save temporary task instructions.

Examples:

"Help me install Docker."

"Write a Python script."

"Explain this error."

"Fix this code."

"Show me how to configure Nginx."

These are requests, not necessarily persistent facts.

============================================================
STABLE MEMORY KEYS
============================================================

Every saveable memory MUST have a stable key.

The key identifies WHAT the memory represents,
not the exact wording.

Example:

"My favorite editor is VS Code."

key:

"favorite_editor"

Later:

"I now prefer Neovim."

The key remains:

"favorite_editor"

Another example:

"I want to become an AI engineer."

key:

"career_goal"

Later:

"I now want to specialize in AI infrastructure."

The appropriate career-goal key should remain stable where
the information represents the same underlying goal.

Use concise snake_case keys.

Examples:

favorite_editor
preferred_programming_language
career_role
career_goal
docker_usage
kubernetes_experience
cloud_platform
current_project
professional_interest

============================================================
MEMORY SENTENCE
============================================================

Rewrite the memory as a complete sentence.

BAD:

"VS Code"

GOOD:

"Jerry's favorite editor is VS Code."

BAD:

"AI engineering"

GOOD:

"Jerry is working toward becoming an AI engineer."

BAD:

"Docker"

GOOD:

"Jerry uses Docker extensively."

The memory must describe Jerry, not merely contain a keyword.

============================================================
MEMORY TYPES
============================================================

Use exactly ONE of these types:

preference
identity
goal
fact

Do NOT invent additional types.

============================================================
IMPORTANCE
============================================================

Use an integer from 1 to 10.

10:
- Identity
- Spouse / immediate family
- Core personal identity
- Extremely important personal preference

9:
- Long-term career goals
- Major life goals
- Major projects
- Important career direction

8:
- Recurring professional skills
- Important technology experience
- Significant ongoing projects

6:
- Useful preferences
- Normal career facts
- Common technology preferences

3:
- Minor preferences

1:
- Trivial information

For explicit long-term career goals, prefer 9.

For major identity statements, prefer 10.

============================================================
DECISION RULE
============================================================

When uncertain, ask:

"Would knowing this information several conversations from now
help Athena understand Jerry better?"

If YES:
save it.

If NO:
do not save it.

============================================================
OUTPUT FORMAT
============================================================

Return EXACTLY ONE valid JSON object.

NEVER return markdown.

NEVER return explanations.

NEVER return multiple JSON objects.

============================================================
SAVEABLE EXAMPLE
============================================================

USER MESSAGE:

"I am working toward becoming an AI engineer."

Correct response:

{
    "save": true,
    "operation": "candidate",
    "memory": "Jerry is working toward becoming an AI engineer.",
    "type": "goal",
    "key": "career_goal",
    "importance": 9
}

============================================================
SAVEABLE EXAMPLE
============================================================

USER MESSAGE:

"My favorite editor is VS Code."

Correct response:

{
    "save": true,
    "operation": "candidate",
    "memory": "Jerry's favorite editor is VS Code.",
    "type": "preference",
    "key": "favorite_editor",
    "importance": 6
}

============================================================
SAVEABLE EXAMPLE
============================================================

USER MESSAGE:

"I use Docker extensively in my work."

Correct response:

{
    "save": true,
    "operation": "candidate",
    "memory": "Jerry uses Docker extensively in his work.",
    "type": "fact",
    "key": "docker_usage",
    "importance": 8
}

============================================================
NON-SAVEABLE EXAMPLE
============================================================

USER MESSAGE:

"What is the difference between Docker and Podman?"

Correct response:

{
    "save": false,
    "operation": "none"
}

============================================================
NON-SAVEABLE EXAMPLE
============================================================

USER MESSAGE:

"Explain Kubernetes to me."

Correct response:

{
    "save": false,
    "operation": "none"
}

============================================================
NON-SAVEABLE EXAMPLE
============================================================

USER MESSAGE:

"Hello Athena."

Correct response:

{
    "save": false,
    "operation": "none"
}

============================================================
FINAL RULE
============================================================

The USER MESSAGE is the source of truth.

The ASSISTANT RESPONSE is context only.

Never manufacture a personal memory from assistant-generated
information.
"""

        # ========================================================
        # CONVERSATION CONTEXT
        # ========================================================

        conversation = f"""
USER MESSAGE:

{user_message}

IMPORTANT:
The USER MESSAGE is the only source from which a memory
candidate may be created.

Extract persistent information only from the USER MESSAGE.

Do not use previous memories.
Do not use assistant responses.
Do not infer information that is not explicitly supported
by the USER MESSAGE.
"""

        logger.info(
            "\n========== MEMORY INPUT ==========\n"
            f"{conversation}"
            "\n=================================="
        )

        # ========================================================
        # CALL LLM
        # ========================================================

        try:

            response = self.client.chat.completions.create(
                model=settings.LLM_MODEL,
                temperature=0,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": conversation,
                    },
                ],
            )

            text = response.choices[0].message.content

            if not text:
                logger.warning(
                    "Memory intelligence returned empty response."
                )

                return {
                    "save": False,
                    "operation": "none",
                }

            text = text.strip()

        except Exception as exc:

            logger.exception(
                f"Memory intelligence LLM failed: {exc}"
            )

            return {
                "save": False,
                "operation": "none",
            }

        logger.info(
            "\n========== MEMORY MANAGER ==========\n"
            f"{text}"
            "\n===================================="
        )

        # ========================================================
        # EXTRACT JSON
        # ========================================================

        result = self._extract_json(text)

        if not result:

            logger.warning(
                "Invalid memory intelligence JSON."
            )

            return {
                "save": False,
                "operation": "none",
            }

        # ========================================================
        # SAVE DECISION
        # ========================================================

        save = result.get("save")

        if save is not True:

            logger.info(
                "Memory intelligence determined that the user "
                "message contains no persistent memory."
            )

            return {
                "save": False,
                "operation": "none",
            }

        # ========================================================
        # OPERATION
        # ========================================================

        operation = (
            str(
                result.get(
                    "operation",
                    "",
                )
            )
            .strip()
            .lower()
        )

        if operation != "candidate":

            logger.warning(
                f"Invalid memory operation returned: {operation}"
            )

            return {
                "save": False,
                "operation": "none",
            }

        # ========================================================
        # EXTRACT MEMORY
        # ========================================================

        memory = str(
            result.get(
                "memory",
                "",
            )
        ).strip()

        memory_type = (
            str(
                result.get(
                    "type",
                    "fact",
                )
            )
            .strip()
            .lower()
        )

        memory_key = (
            str(
                result.get(
                    "key",
                    "",
                )
            )
            .strip()
            .lower()
        )

        importance = result.get(
            "importance",
            5,
        )

        # ========================================================
        # VALIDATE MEMORY TEXT
        # ========================================================

        if len(memory) < 10:

            logger.warning(
                "Memory candidate is too short."
            )

            return {
                "save": False,
                "operation": "none",
            }

        # ========================================================
        # VALIDATE KEY
        # ========================================================

        if not memory_key:

            logger.warning(
                "Memory candidate has no stable key."
            )

            return {
                "save": False,
                "operation": "none",
            }

        # Normalize key
        memory_key = re.sub(
            r"[^a-z0-9_]+",
            "_",
            memory_key,
        ).strip("_")

        if not memory_key:

            logger.warning(
                "Memory candidate key became empty after normalization."
            )

            return {
                "save": False,
                "operation": "none",
            }

        # ========================================================
        # VALIDATE TYPE
        # ========================================================

        allowed_types = {
            "preference",
            "identity",
            "goal",
            "fact",
        }

        if memory_type not in allowed_types:

            logger.warning(
                f"Invalid memory type: {memory_type}"
            )

            return {
                "save": False,
                "operation": "none",
            }

        # ========================================================
        # NORMALIZE IMPORTANCE
        # ========================================================

        try:

            importance = int(importance)

        except (
            TypeError,
            ValueError,
        ):

            importance = 5

        importance = max(
            1,
            min(
                10,
                importance,
            ),
        )

        # ========================================================
        # RETURN CANDIDATE
        # ========================================================

        logger.success(
            "Memory candidate extracted successfully."
        )

        logger.info(
            f"Candidate memory: {memory}"
        )

        logger.info(
            f"Candidate type: {memory_type}"
        )

        logger.info(
            f"Candidate key: {memory_key}"
        )

        logger.info(
            f"Candidate importance: {importance}"
        )

        return {
            "save": True,
            "operation": "candidate",
            "memory": memory,
            "type": memory_type,
            "key": memory_key,
            "importance": importance,
        }


# ================================================================
# GLOBAL INSTANCE
# ================================================================

memory_intelligence = MemoryIntelligence()
