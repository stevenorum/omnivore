#!/usr/bin/env python3

import boto3
from datetime import datetime, timedelta
import src.geat.gson as json

SHELL_COLORS = {
    'PURPLE':'\033[95m',
    'BLUE':'\033[94m',
    'GREEN':'\033[92m',
    'YELLOW':'\033[93m',
    'RED':'\033[91m',
    'RESET':'\033[0m'
}

def color(s, c):
    return '{}{}{}'.format(SHELL_COLORS.get(c.upper(), SHELL_COLORS["BLUE"]), s, SHELL_COLORS["RESET"])

def color_status(status):
    if status.upper() == "SUCCEEDED":
        return color(status, "BLUE")
    if status.upper() == "FAILED":
        return color(status, "RED")
    return color(status, "YELLOW")

with open("private_vars.json") as f:
    private = json.load(f)

region_name = private["region_name"]
profile_name = private["profile_name"]
pipeline_name = private["pipeline_name"]


boto3.setup_default_session(region_name=region_name, profile_name=profile_name)

def sify(n):
    return "" if n == 1 else "s"

def format_part(n, name):
    return ["{} {}{}".format(n, name, sify(n))] if n else []

def format_time(dt, approximate=True):
    ago = datetime.now().replace(tzinfo=None) - dt.replace(tzinfo=None)
    seconds = ago.seconds % 60
    minutes = int(ago.seconds/60) % 60
    hours = int(ago.seconds/3600)
    days = ago.days

    if approximate:
        total_seconds = ago.seconds + ago.days*24*60*60
        total_minutes = int(total_seconds/60)
        total_hours = int(total_minutes/60)

        if total_minutes > 5:
            minutes += 1 if seconds >= 30 else 0
            seconds = 0
            if total_hours > 12:
                hours += 1 if minutes >= 30 else 0
                minutes = 0
                if days > 3:
                    days += 1 if hours >= 12 else 0
                    hours = 0
    while seconds >= 60:
        # Shouldn't be necessary, but whatever.
        minutes += 1
        seconds -= 60
    while minutes >= 60:
        hours += 1
        minutes -= 60
    while hours > 23:
        days += 1
        hours -= 24

    dateparts = []
    dateparts.extend(format_part(days, "day"))
    dateparts.extend(format_part(hours, "hour"))
    dateparts.extend(format_part(minutes, "minute"))
    dateparts.extend(format_part(seconds, "second"))
    return ", ".join(dateparts)

copi = boto3.client("codepipeline")

print("Pipeline structure:\n")

pipeline = copi.get_pipeline(name=pipeline_name)
stages = pipeline["pipeline"]["stages"]
stage_names = [s["name"] for s in stages]
actions = {s["name"]:[a["name"] for a in s["actions"]] for s in stages}
for name in stage_names:
    print("Stage: {}".format(name))
    for action in actions[name]:
        print("  Action: {}".format(action))
pipeline_state = copi.get_pipeline_state(name=pipeline_name)

print("\nPipeline state:\n")

stages = pipeline_state["stageStates"]
for stage in stages:
    print("Stage: {} ({})".format(stage["stageName"], color_status(stage["latestExecution"]["status"])))
    for action in stage["actionStates"]:
        print("  Action: {} ({} as of {} ago)".format(action["actionName"], color_status(action["latestExecution"]["status"]), format_time(action["latestExecution"]["lastStatusChange"])))

# print(json.dumps(pipeline, indent=2, sort_keys=True, ignore_type_error=True))
# print(json.dumps(pipeline_state, indent=2, sort_keys=True, ignore_type_error=True))
