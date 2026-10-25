#!/usr/bin/env python3
import argparse
import json

class SOVDLab:
    def __init__(self):
        self.entities={
            "powertrain":{"capabilities":["faults","measurements","configuration"],"faults":[{"id":"P0300","status":"active","severity":"high"}],"measurements":{"engine_speed":850,"coolant_temp":82},"configuration":{"mode":"normal"}},
            "body":{"capabilities":["measurements"],"faults":[],"measurements":{"battery_voltage":12.4},"configuration":{}}
        }
    def handle(self,method,path,body=None):
        parts=[p for p in path.split("/") if p]
        if parts[:2]!=["api","v1"]: return 404,{"error":"not_found"}
        if len(parts)==3 and parts[2]=="entities" and method=="GET":
            return 200,{"entities":[{"id":k,"capabilities":v["capabilities"]} for k,v in sorted(self.entities.items())]}
        if len(parts)<4 or parts[2]!="entities" or parts[3] not in self.entities: return 404,{"error":"entity_not_found"}
        entity=self.entities[parts[3]]
        if len(parts)==5 and parts[4]=="faults" and method=="GET": return 200,{"entity":parts[3],"faults":entity["faults"]}
        if len(parts)==5 and parts[4]=="measurements" and method=="GET": return 200,{"entity":parts[3],"measurements":entity["measurements"]}
        if len(parts)==6 and parts[4]=="measurements" and method=="GET":
            key=parts[5]
            if key not in entity["measurements"]: return 404,{"error":"measurement_not_found"}
            return 200,{"entity":parts[3],"name":key,"value":entity["measurements"][key]}
        if len(parts)==5 and parts[4]=="configuration":
            if method=="GET": return 200,{"entity":parts[3],"configuration":entity["configuration"]}
            if method=="PUT" and isinstance(body,dict):
                unknown=set(body)-set(entity["configuration"])
                if unknown: return 400,{"error":"unknown_configuration","keys":sorted(unknown)}
                entity["configuration"].update(body)
                return 200,{"entity":parts[3],"configuration":entity["configuration"]}
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
        entity,key=a.path.split(".",1); status,payload=lab.handle("GET","/api/v1/entities/"+entity+"/measurements/"+key)
    elif a.cmd=="set": status,payload=lab.handle("PUT","/api/v1/entities/"+a.entity+"/configuration",{a.key:a.value})
    else: p.error("choose list, faults, measure, or set")
    print(json.dumps(payload,indent=2,ensure_ascii=False)); return 0 if status<400 else 1
if __name__=="__main__": raise SystemExit(cli())
