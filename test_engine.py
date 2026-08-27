import tempfile, unittest
from pathlib import Path
from engine import add_case, detect, initialise_database, list_flagged_cases, save_review
class Tests(unittest.TestCase):
 def test_detection(self): self.assertGreaterEqual(len(detect({"id":"x","customer_name":"t","amount":200000,"hour":2,"new_device":True,"device_trusted":False,"beneficiary_new":True},"transaction")),4)
 def test_storage(self):
  with tempfile.TemporaryDirectory() as d:
   db=Path(d)/"x.db"; initialise_database(db); c=list_flagged_cases(db)[0]; save_review(db,c["case_id"],"Analyst","agree","Checked"); self.assertEqual(list_flagged_cases(db)[0]["reviewer"],"Analyst")
 def test_manual_case_persists(self):
  with tempfile.TemporaryDirectory() as d:
   db=Path(d)/"x.db"; initialise_database(db)
   case=add_case(db,{"case_type":"signup","applicant_name":"New Applicant","country":"IN","document_resubmits":2,"name_matches_document":False,"address_matches_document":False,"device_risk":"high"})
   self.assertIn(case["case_id"],[x["case_id"] for x in list_flagged_cases(db)])
if __name__=="__main__": unittest.main()
