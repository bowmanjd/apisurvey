"""Survey server."""
import asyncio
from collections.abc import Iterable
from datetime import datetime

import aiosqlite
import orjson
from async_lru import alru_cache


async def dbexecute(
    sql: str,
    params: dict | list | None = None,
    fetchone: bool = False,
    fetchall: bool = False,
) -> Iterable[aiosqlite.Row] | aiosqlite.Row | None:
    """Execute SQLite database query.

    Arguments:
        sql: the SQL query text
        params: tuple of values to interpolate in query
        fetchone: whether or not to fetch only one result
        fetchall: whether or not to fetch all results

    Returns:
        data from result
    """
    data = None
    if params is None:
        params = {}

    async with aiosqlite.connect("survey.db", isolation_level=None) as db:
        await db.execute("pragma journal_mode=wal;")
        await db.execute("pragma synchronous=normal;")
        await db.execute("pragma temp_store=memory;")
        await db.execute("pragma mmap_size=8589934592;")
        cursor = await db.cursor()
        if isinstance(params, dict):
            await cursor.execute(sql, params)
        elif isinstance(params, list):
            await cursor.executemany(sql, params)
        if fetchone:
            data = await cursor.fetchone()
        if fetchall:
            data = await cursor.fetchall()
    return data


@alru_cache
async def get_surveys() -> dict:
    """Generate/cache dict of surveys, questions, and expiration timestamps.

    Returns:
        dict with title as key
    """
    result = await dbexecute(
        "SELECT json_group_object(title, json_object('question',question,"
        "'expiry',expiry)) FROM survey;",
        fetchone=True,
    )
    surveys = {}
    if isinstance(result, tuple):
        surveys = orjson.loads(str(result[0]))
    return surveys


async def get_action(path: str) -> str:
    """Get action from path string.

    Args:
        path: path string from URL

    Returns:
        action name
    """
    action = path.strip("/").split("/", 2)[0]
    return action


async def submit_survey(survey: str, answer: str):
    """Submit survey answer.

    Args:
        survey: name of survey
        answer: text of survey response
    """


async def app(scope, proto):
    """RSGI app.

    Arguments:
        scope: the scope
        proto: the protocol
    """
    message = ""
    body_json = '""'
    agent = scope.headers.get("user-agent")
    surveys = await get_surveys()
    action = await get_action(scope.path)
    if not agent.casefold().startswith("python"):
        code = 451
        message = "Try using a Python HTTP client"
    elif action not in surveys:
        code = 404
        message = f"Could not find any survey called {action}"
    else:
        code = 200
        if scope.method == "POST":
            answer = await proto()
            answer = answer.decode()
            await dbexecute(
                "INSERT INTO response(title,data,agent) "
                "VALUES (:title,:data,:agent);",
                {"title": action, "data": answer, "agent": agent},
            )
            body_json = f'"Successfully submitted answer \\"{answer}\\"."'
        elif scope.method == "GET":
            answer_list = await dbexecute(
                "SELECT json_group_array(data) FROM response;", fetchone=True
            ) or ("[]")
            if isinstance(answer_list, tuple):
                body_json = answer_list[0]

    if code != 200:
        body = {"error": {"code": code, "message": message}}
        body_json = orjson.dumps(
            body, option=orjson.OPT_INDENT_2 | orjson.OPT_APPEND_NEWLINE
        ).decode()
    proto.response_str(code, [("content-type", "application/json")], body_json)


async def dbinit():
    """Initialize database."""
    await dbexecute(
        "CREATE TABLE IF NOT EXISTS response ("
        "title TEXT, "
        "created DATETIME NOT NULL DEFAULT (datetime(CURRENT_TIMESTAMP, 'localtime')), "
        "data TEXT,"
        "agent TEXT"
        ");"
    )
    await dbexecute(
        "CREATE TABLE IF NOT EXISTS survey ("
        "title TEXT, "
        "created DATETIME NOT NULL DEFAULT (datetime(CURRENT_TIMESTAMP, 'localtime')), "
        "question TEXT, "
        "expiry FLOAT NULL"
        ");"
    )
    surveys = [
        {
            "title": "favorite",
            "question": (
                "What is your favorite type of snake OR favorite Monty Python quote?"
            ),
            "expiry": datetime.timestamp(datetime(2022, 12, 2, 10, 0)),
        },
        {
            "title": "automation",
            "question": (
                "Name an automation tool or language you use for configuring or "
                "managing systems."
            ),
            "expiry": datetime.timestamp(datetime(2022, 12, 2, 10, 0)),
        },
        {
            "title": "task",
            "question": "What is a task you wish you could script or automate?",
            "expiry": datetime.timestamp(datetime(2022, 12, 2, 10, 0)),
        },
    ]
    await dbexecute(
        "INSERT INTO survey (title, question, expiry) "
        "VALUES (:title, :question, :expiry);",
        surveys,
    )
    data = await dbexecute("SELECT * FROM response;", fetchall=True) or []
    for row in data:
        print(row)


if __name__ == "__main__":
    asyncio.run(dbinit())

    print(asyncio.run(get_surveys()))
