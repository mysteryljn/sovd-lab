import contextlib
import io
import unittest
from sovd import SOVDLab, cli

class SovdTests(unittest.TestCase):
    def test_discovery_and_measurement(self):
        lab=SOVDLab(); code,payload=lab.handle("GET","/api/v1/entities")
        self.assertEqual(code,200); self.assertEqual(len(payload["entities"]),2)
        code,payload=lab.handle("GET","/api/v1/entities/powertrain/measurements/engine_speed")
        self.assertEqual((code,payload["value"]),(200,850))
    def test_reject_unknown_configuration(self):
        code,payload=SOVDLab().handle("PUT","/api/v1/entities/powertrain/configuration",{"unknown":"x"})
        self.assertEqual(code,400); self.assertIn("unknown",payload["keys"])

    def test_unsupported_capabilities_are_not_exposed(self):
        lab=SOVDLab()
        code,payload=lab.handle("GET","/api/v1/entities/body/faults")
        self.assertEqual((code,payload),(404,{"error":"capability_not_supported","capability":"faults"}))
        code,payload=lab.handle("PUT","/api/v1/entities/body/configuration",{})
        self.assertEqual((code,payload),(404,{"error":"capability_not_supported","capability":"configuration"}))

    def test_read_responses_cannot_mutate_server_state(self):
        lab=SOVDLab()

        code, faults = lab.handle("GET", "/api/v1/entities/powertrain/faults")
        self.assertEqual(code, 200)
        faults["faults"][0]["severity"] = "low"
        faults["faults"].append({"id": "INJECTED"})

        code, measurements = lab.handle("GET", "/api/v1/entities/powertrain/measurements")
        self.assertEqual(code, 200)
        measurements["measurements"]["engine_speed"] = 0

        code, configuration = lab.handle("GET", "/api/v1/entities/powertrain/configuration")
        self.assertEqual(code, 200)
        configuration["configuration"]["mode"] = "sport"

        code, entities = lab.handle("GET", "/api/v1/entities")
        self.assertEqual(code, 200)
        entities["entities"][0]["capabilities"].append("injected")

        self.assertEqual(
            lab.handle("GET", "/api/v1/entities/powertrain/faults")[1]["faults"],
            [{"id": "P0300", "status": "active", "severity": "high"}],
        )
        self.assertEqual(
            lab.handle("GET", "/api/v1/entities/powertrain/measurements")[1]["measurements"]["engine_speed"],
            850,
        )
        self.assertEqual(
            lab.handle("GET", "/api/v1/entities/powertrain/configuration")[1]["configuration"],
            {"mode": "normal"},
        )
        capabilities = {
            item["id"]: item["capabilities"]
            for item in lab.handle("GET", "/api/v1/entities")[1]["entities"]
        }
        self.assertEqual(capabilities["powertrain"], ["faults", "measurements", "configuration"])

    def test_configuration_update_copies_caller_owned_values(self):
        lab = SOVDLab()
        body = {"mode": "sport"}
        code, payload = lab.handle("PUT", "/api/v1/entities/powertrain/configuration", body)
        self.assertEqual(code, 200)
        body["mode"] = "eco"
        payload["configuration"]["mode"] = "track"
        self.assertEqual(
            lab.handle("GET", "/api/v1/entities/powertrain/configuration")[1]["configuration"],
            {"mode": "sport"},
        )

    def test_configuration_update_rejects_type_confusion(self):
        lab = SOVDLab()
        code, payload = lab.handle(
            "PUT", "/api/v1/entities/powertrain/configuration", {"mode": {"value": "sport"}}
        )
        self.assertEqual(
            (code, payload),
            (400, {"error": "invalid_configuration_type", "keys": ["mode"]}),
        )
        self.assertEqual(
            lab.handle("GET", "/api/v1/entities/powertrain/configuration")[1]["configuration"],
            {"mode": "normal"},
        )

    def test_configuration_update_rejects_non_string_keys_without_crashing(self):
        lab = SOVDLab()
        code, payload = lab.handle(
            "PUT",
            "/api/v1/entities/powertrain/configuration",
            {1: "unexpected", "unknown": "also unexpected"},
        )
        self.assertEqual((code, payload), (400, {"error": "invalid_configuration_keys"}))
        self.assertEqual(
            lab.handle("GET", "/api/v1/entities/powertrain/configuration")[1]["configuration"],
            {"mode": "normal"},
        )

    def test_configuration_put_rejects_non_object_payload(self):
        lab = SOVDLab()
        for body in (None, [], "sport"):
            code, payload = lab.handle(
                "PUT", "/api/v1/entities/powertrain/configuration", body
            )
            self.assertEqual((code, payload), (400, {"error": "invalid_configuration"}))
        self.assertEqual(
            lab.handle("GET", "/api/v1/entities/powertrain/configuration")[1]["configuration"],
            {"mode": "normal"},
        )

    def test_malformed_paths_are_rejected_without_crashing(self):
        code, payload = SOVDLab().handle("GET", None)
        self.assertEqual((code, payload), (400, {"error": "invalid_path"}))

    def test_measure_cli_rejects_malformed_path(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = cli(["measure", "powertrain"])
        self.assertEqual(status, 1)
        self.assertIn('"invalid_measurement_path"', output.getvalue())
if __name__=="__main__": unittest.main()
