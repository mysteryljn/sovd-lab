import unittest
from sovd import SOVDLab

class SovdTests(unittest.TestCase):
    def test_discovery_and_measurement(self):
        lab=SOVDLab(); code,payload=lab.handle("GET","/api/v1/entities")
        self.assertEqual(code,200); self.assertEqual(len(payload["entities"]),2)
        code,payload=lab.handle("GET","/api/v1/entities/powertrain/measurements/engine_speed")
        self.assertEqual((code,payload["value"]),(200,850))
    def test_reject_unknown_configuration(self):
        code,payload=SOVDLab().handle("PUT","/api/v1/entities/powertrain/configuration",{"unknown":"x"})
        self.assertEqual(code,400); self.assertIn("unknown",payload["keys"])
if __name__=="__main__": unittest.main()
