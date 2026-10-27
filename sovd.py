#!/usr/bin/env python3
import argparse
import copy
import json

class SOVDLab:
    def __init__(self):
        self.entities={
            "powertrain":{"capabilities":["faults","measurements","configuration"],"faults":[{"id":"P0300","status":"active","severity":"high"}],"measurements":{"engine_speed":850,"coolant_temp":82},"configuration":{"mode":"normal"}},
            "body":{"capabilities":["measurements"],"faults":[],"measurements":{"battery_voltage":12.4},"configuration":{}}
        }
    def handle(self,method,path,body=None):
        # Requests come from an external transport, so a malformed path must
        # be rejected as data instead of raising AttributeError from
        # ``path.split`` and terminating the caller.
        if not isinstance(path, str):
            return 400,{"error":"invalid_path"}
        # Do not silently normalize empty path segments.  An authorization or
        # audit layer may compare the literal URI while a backend that removes
        # empty segments would route it to a different resource (for example,
        # ``//configuration``), creating a path-confusion boundary.
        parts=path.split("/")
        if parts and parts[0]=="":
            parts=parts[1:]
        if not parts or any(part=="" for part in parts):
            return 400,{"error":"invalid_path"}
        if parts[:2]!=["api","v1"]: return 404,{"error":"not_found"}
        if len(parts)==3 and parts[2]=="entities" and method=="GET":
            return 200,{"entities":[{"id":k,"capabilities":copy.deepcopy(v["capabilities"])} for k,v in sorted(self.entities.items())]}
        if len(parts)<4 or parts[2]!="entities" or parts[3] not in self.entities: return 404,{"error":"entity_not_found"}
        entity=self.entities[parts[3]]
        if len(parts)==5 and parts[4]=="faults" and method=="GET":
            if "faults" not in entity["capabilities"]:
                return 404,{"error":"capability_not_supported","capability":"faults"}
            return 200,{"entity":parts[3],"faults":copy.deepcopy(entity["faults"])}
        if len(parts)==5 and parts[4]=="measurements" and method=="GET":
            if "measurements" not in entity["capabilities"]:
                return 404,{"error":"capability_not_supported","capability":"measurements"}
            return 200,{"entity":parts[3],"measurements":copy.deepcopy(entity["measurements"])}
        if len(parts)==6 and parts[4]=="measurements" and method=="GET":
            if "measurements" not in entity["capabilities"]:
                return 404,{"error":"capability_not_supported","capability":"measurements"}
            key=parts[5]
            if key not in entity["measurements"]: return 404,{"error":"measurement_not_found"}
            return 200,{"entity":parts[3],"name":key,"value":copy.deepcopy(entity["measurements"][key])}
        if len(parts)==5 and parts[4]=="configuration":
            if "configuration" not in entity["capabilities"]:
                return 404,{"error":"capability_not_supported","capability":"configuration"}
            if method=="GET": return 200,{"entity":parts[3],"configuration":copy.deepcopy(entity["configuration"])}
            if method=="PUT" and not isinstance(body,dict):
                # PUT is a supported operation on this resource.  A malformed
                # payload must therefore be reported as bad input; returning
                # 405 makes clients believe the operation itself is unsupported
                # and can trigger incorrect fallback/retry behavior.
                return 400,{"error":"invalid_configuration"}
            if method=="PUT" and isinstance(body,dict):
                # JSON object member names are strings.  The in-memory API is
                # also callable directly, so reject Python mappings with
                # non-string keys before set/sort operations below.  Without
                # this guard a mixed key mapping (for example ``{1: "x",
                # "unknown": "y"}``) raises TypeError while sorting the
                # unknown-key response and can terminate a request handler.
                if any(not isinstance(key,str) for key in body):
                    return 400,{"error":"invalid_configuration_keys"}
                unknown=set(body)-set(entity["configuration"])
                if unknown: return 400,{"error":"unknown_configuration","keys":sorted(unknown)}
                # Configuration values have a stable type contract.  Accepting
                # arbitrary JSON here can poison the in-memory model (for
                # example, replacing the string ``mode`` with an object),
                # causing clients that consume the diagnostic response to
                # fail later.  Keep updates compatible with the value already
                # advertised by the entity.
                invalid = [
                    key for key, value in body.items()
                    if type(value) is not type(entity["configuration"][key])
                ]
                if invalid:
                    return 400,{"error":"invalid_configuration_type","keys":sorted(invalid)}
                encoding_invalid=[]
                for key, value in body.items():
                    if isinstance(value, str):
                        try:
                            value.encode("utf-8")
                        except UnicodeEncodeError:
                            encoding_invalid.append(key)
                if encoding_invalid:
                    # JSON can carry escaped lone surrogates, but they cannot
                    # be written to a UTF-8 response when ensure_ascii=False.
                    # Reject them before they poison server state or crash the
                    # transport while serializing a diagnostic response.
                    return 400,{"error":"invalid_configuration_encoding","keys":sorted(encoding_invalid)}
                entity["configuration"].update(copy.deepcopy(body))
                return 200,{"entity":parts[3],"configuration":copy.deepcopy(entity["configuration"])}
        return 405,{"error":"method_not_allowed"}

def cli(argv=None):
    p=argparse.ArgumentParser(description="Run a local SOVD diagnostic model"); sub=p.add_subparsers(dest="cmd")
    sub.add_parser("list")
    f=sub.add_parser("faults"); f.add_argument("entity")
    m=sub.add_parser("measure"); m.add_argument("path")
    s=sub.add_parser("set"); s.add_argument("entity"); s.add_argument("key"); s.add_argument("value")
    a=p.parse_args(argv); lab=SOVDLab()
    if a.cmd=="list": status,payload=lab.handle("GET","/api/v1/entities")
    elif a.cmd=="faults": status,payload=lab.handle("GET","/api/v1/entities/"+a.entity+"/faults")
    elif a.cmd=="measure":
        if "." not in a.path:
            status,payload=400,{"error":"invalid_measurement_path","message":"expected ENTITY.MEASUREMENT"}
        else:
            entity,key=a.path.split(".",1)
            if not entity or not key:
                status,payload=400,{"error":"invalid_measurement_path","message":"expected ENTITY.MEASUREMENT"}
            else:
                status,payload=lab.handle("GET","/api/v1/entities/"+entity+"/measurements/"+key)
    elif a.cmd=="set": status,payload=lab.handle("PUT","/api/v1/entities/"+a.entity+"/configuration",{a.key:a.value})
    else: p.error("choose list, faults, measure, or set")
    print(json.dumps(payload,indent=2,ensure_ascii=False)); return 0 if status<400 else 1
if __name__=="__main__": raise SystemExit(cli())
