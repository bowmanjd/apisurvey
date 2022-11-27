#!/usr/bin/env python3
"""Simple survey API client."""
import argparse
import json
import pprint
from urllib.request import Request
from urllib.request import urlopen

SERVER = "http://localhost:8000"
HEADERS = {"Content-Type": "application/json; charset=UTF-8"}


def submit(survey: str, answer: str) -> str:
    httprequest = Request(f"{SERVER}/{survey}", data=answer.encode(), headers=HEADERS)

    with urlopen(httprequest) as response:
        raw = response.read().decode()
        result = json.loads(raw)
    return result


def show(survey: str) -> str:
    httprequest = Request(f"{SERVER}/{survey}", headers=HEADERS)

    with urlopen(httprequest) as response:
        raw = response.read().decode()
        result = json.loads(raw)
    return result


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("survey", help="The name of the survey")
    parser.add_argument("-a", "--answer", help="The answer to the survey")
    args = parser.parse_args()
    if args.answer:
        result = submit(args.survey, args.answer)
        pprint.pprint(result)
    else:
        result = show(args.survey)
        for answer in result:
            print(answer)


if __name__ == "__main__":
    run()
