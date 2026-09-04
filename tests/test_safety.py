from app.safety import remote_ok,web_ok,eligible,fingerprint
def test_remote_double_lock():
 assert remote_ok("Remote India")
 assert not remote_ok("Hybrid - India")
 assert not remote_ok("Remote after probation")
 assert not remote_ok("Remote status not specified")
def test_web_double_lock():
 assert web_ok("React Developer","")
 assert web_ok("AI Engineer","Build web applications with React and Node.js")
 assert not web_ok("Android Developer","")
 assert not web_ok("Data Scientist","")
def test_job_eligibility():
 assert eligible({"title":"Full Stack Developer","description":"React web application","location":"India","remote_status":"Remote"})
 assert not eligible({"title":"Full Stack Developer","description":"React web application","location":"India","remote_status":"Hybrid"})
def test_fingerprint_stable():
 assert fingerprint("Acme","React Developer","https://example.com/job")==fingerprint(" acme "," react developer ","https://example.com/job")
