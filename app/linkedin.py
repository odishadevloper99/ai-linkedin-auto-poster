from .http import request
class LinkedIn:
 def __init__(self,c):self.c=c
 def h(self):return {"Authorization":f"Bearer {self.c.linkedin_token}","Content-Type":"application/json","X-Restli-Protocol-Version":"2.0.0","Linkedin-Version":self.c.linkedin_version}
 def publish(self,caption,image,content_type='image/jpeg'):
    if not self.c.linkedin_token or not self.c.linkedin_urn:raise RuntimeError("LinkedIn token/URN not configured")
    r=request("POST","https://api.linkedin.com/rest/images?action=initializeUpload",headers=self.h(),json={"initializeUploadRequest":{"owner":self.c.linkedin_urn}},timeout=self.c.timeout,retries=self.c.retries)
    if not r.ok:raise RuntimeError(f"LinkedIn image init HTTP {r.status_code}: {r.text[:1000]}")
    v=r.json()["value"]; urn,url=v["image"],v["uploadUrl"]
    r=request("PUT",url,headers={"Content-Type":content_type},data=image,timeout=self.c.timeout,retries=self.c.retries)
    if not 200<=r.status_code<300:raise RuntimeError(f"LinkedIn image upload HTTP {r.status_code}: {r.text[:500]}")
    body={"author":self.c.linkedin_urn,"commentary":caption,"visibility":"PUBLIC","distribution":{"feedDistribution":"MAIN_FEED","targetEntities":[],"thirdPartyDistributionChannels":[]},"content":{"media":{"altText":"Professional technology editorial image","id":urn}},"lifecycleState":"PUBLISHED","isReshareDisabledByAuthor":False}
    r=request("POST","https://api.linkedin.com/rest/posts",headers=self.h(),json=body,timeout=self.c.timeout,retries=self.c.retries)
    if r.status_code!=201:raise RuntimeError(f"LinkedIn post HTTP {r.status_code}: {r.text[:1200]}")
    pid=r.headers.get("x-restli-id") or r.json().get("id")
    if not pid:raise RuntimeError("LinkedIn returned no post ID")
    return pid
 def url(self,pid):return "https://www.linkedin.com/feed/update/"+pid+"/" if pid.startswith(("urn:li:share:","urn:li:ugcPost:")) else None
