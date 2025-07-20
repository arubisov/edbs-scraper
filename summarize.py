import argparse
import logging
from datetime import datetime
from pathlib import Path

from jinja2 import BaseLoader, Environment
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_random_exponential

from config import settings
from prompt import MESSAGE_TEMPLATE, SUMMARY_PREAMBLE, SYSTEM_PROMPT
from utils.logconfig import setup_logger

lgg = setup_logger(logging.INFO)

_jinja_env = Environment(loader=BaseLoader())
_prompt_template = _jinja_env.from_string(MESSAGE_TEMPLATE)

client = OpenAI(api_key=settings.openai_api_key)


def build_messages(text: str, from_date: str, to_date: str) -> list[dict[str, str]]:
    rendered_prompt = _prompt_template.render(
        {"FILE_DIFF": text, "FROM_DATE": from_date, "TO_DATE": to_date}
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": rendered_prompt},
    ]


@retry(wait=wait_random_exponential(max=60), stop=stop_after_attempt(1))
def summarize_diff(text: str, from_date: str, to_date: str) -> str:
    response = client.responses.create(
        model=settings.openai_model_version,
        input=build_messages(text, from_date, to_date),
        temperature=0,
    )
    return response.output_text


def prepend_summary_to_file(filepath: str, summary: str) -> None:
    with open(filepath, "r") as f:
        original_content = f.read()

    with open(filepath, "w") as f:
        f.write(summary + "\n\n### Detailed changes\n\n" + original_content)


def main(filepath: str, from_date: str, to_date: str) -> None:
    with open(filepath, "r") as f:
        text = f.read()

    summary = summarize_diff(text, from_date, to_date)

    preamble = _jinja_env.from_string(SUMMARY_PREAMBLE).render(
        {"FROM_DATE": from_date, "TO_DATE": to_date}
    )

    prepend_summary_to_file(filepath, preamble + summary)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Summarize the diff file into plain language.")
    parser.add_argument(
        "filepath",
        type=str,
        help="Path to the diff file",
    )
    args = parser.parse_args()

    filepath = Path(args.filepath)
    if not filepath.is_file():
        parser.error(f"{filepath!r} is not a valid file")

    try:
        old_timestamp, new_timestamp = filepath.name.split(".")[0].split("_")
        from_date = datetime.strptime(old_timestamp, "%d%m%y-%H%M%S").strftime("%Y-%m-%dT%H:%M:%S")
        to_date = datetime.strptime(new_timestamp, "%d%m%y-%H%M%S").strftime("%Y-%m-%dT%H:%M:%S")
    except Exception as e:
        parser.error(
            f"{filepath!r} does not have the expect format <date_from>_<date_to>.diff.txt"
        )

    main(filepath, from_date, to_date)
