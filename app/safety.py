import re,hashlib
ALLOWED=["web developer","website developer","frontend developer","front-end developer","backend developer","back-end developer","full stack developer","full-stack developer","full stack engineer","full-stack web developer","react developer","react.js developer","next.js developer","javascript developer","typescript developer","node.js developer","python web developer","django developer","flask developer","mern developer","web application developer","ai + web developer","ai-powered web developer","ai web application developer"]
REJECT=["android developer","ios developer","mobile developer","data scientist","data analyst","devops","cloud engineer","cybersecurity","qa","tester","hardware","embedded","network engineer","sales","marketing","human resources","customer support","product manager"]
REMOTE_OK=["remote","fully remote","remote worldwide","remote india","remote - india","remote-first","work from home"]
REMOTE_BAD=["on-site","onsite","hybrid","partially remote","remote after probation","hybrid with regular office attendance","office-based"]
def norm(s):return re.sub(r"\s+"," ",(s or "").strip().lower())
def remote_ok(text):
    t=norm(text)
    return not any(x in t for x in REMOTE_BAD) and any(x in t for x in REMOTE_OK)
def web_ok(title,desc=""):
    t=norm(title);d=norm(desc)
    if any(x in t for x in REJECT):return False
    return any(x in t for x in ALLOWED) or (("web application" in d or "web development" in d or "website development" in d) and not any(x in t for x in REJECT))
def fingerprint(company,title,url):return hashlib.sha256("|".join(map(norm,[company,title,url])).encode()).hexdigest()
def eligible(j):return remote_ok(" ".join(str(j.get(k,"")) for k in ["title","description","location","remote_status"])) and web_ok(j.get("title",""),j.get("description",""))
