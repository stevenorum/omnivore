#!/usr/bin/env python

import json
import os
import sys

input_template_file = sys.argv[1]
output_template_file = sys.argv[2]
with open(input_template_file) as f:
    template = json.load(f)

def handle_functions(temp):
    if isinstance(temp, (str,int,float,bool)):
        return temp
    if isinstance(temp,(list,tuple)):
        return [handle_functions(t) for t in temp]
    if isinstance(temp, dict):
        if len(temp) == 1 and list(temp.keys())[0].startswith("Fn::Static::"):
            key = list(temp.keys())[0]
            if key == "Fn::Static::JSON2String": # handles functions inside the blob first
                return json.dumps(handle_functions(temp[key]), separators=(',',':'))
            if key == "Fn::Static::Ignore": # Don't try to perform static functions inside this block.
                return temp[key]
            if key == "Fn::Static::LoadFile":
                typename = temp[key][0]
                filename = temp[key][1]
                with open(filename) as f:
                    if typename == "TEXT":
                        return f.read()
                    if typename == "JSON":
                        return json.load(f)
            raise RuntimeError("No match found for static function '{}' and the given arguments!".format(key))
        return {k:handle_functions(temp[k]) for k in temp}
    return temp

def jsonify(t):
    return json.dumps(t, separators=(',',':'))

pre_temp = jsonify(template)
template = handle_functions(template)

while pre_temp != jsonify(template):
    pre_temp = jsonify(template)
    template = handle_functions(template)

with open(output_template_file, "w") as f:
    json.dump(template, f, indent=2, sort_keys=True)
