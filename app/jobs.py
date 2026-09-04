import html,re
from .http import request
from .safety import eligible,fingerprint
class Sources:
 def __init__(self,c):self.c=c
 def remotive(self):
    if not self.c.remotive_enabled:return []
    d=request("GET",self.c.remotive_url,timeout=self.c.timeout,retries=self.c.retries).json().get("jobs",[]);o=[]
    for j in d:o.append({"source":"Remotive","url":j.get("url",""),"company":j.get("company_name",""),"title":j.get("title",""),"description":re.sub("<[^>]+>"," ",html.unescape(j.get("description",""))),"location":j.get("candidate_required_location",""),"remote_status":"Remote","salary":j.get("salary") or "Not disclosed","experience":"Not specified","skills":j.get("tags") or [],"posted_at":j.get("publication_date")})
    return o
 def arbeit(self):
    if not self.c.arbeitnow_enabled:return []
    d=request("GET",self.c.arbeitnow_url,timeout=self.c.timeout,retries=self.c.retries).json().get("data",[]);o=[]
    for j in d:o.append({"source":"Arbeitnow","url":j.get("url",""),"company":j.get("company_name",""),"title":j.get("title",""),"description":re.sub("<[^>]+>"," ",html.unescape(j.get("description",""))),"location":j.get("location",""),"remote_status":"Remote" if j.get("remote") else "","salary":"Not disclosed","experience":"Not specified","skills":j.get("tags") or [],"posted_at":None})
    return o
 def discover(self):
    all=[]
    for f in (self.remotive,self.arbeit):
     try:all+=f()
     except Exception:pass
    out={}
    for j in all:
     if j.get("url") and eligible(j):
      j["fingerprint"]=fingerprint(j["company"],j["title"],j["url"]);out[j["fingerprint"]]=j
    return list(out.values())
