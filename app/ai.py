import json,re
from .http import request
class AI:
 def __init__(self,c):self.c=c
 def _chat(self,prompt,system,base_url,api_key,model,provider):
    if not api_key:raise RuntimeError(f"{provider} API key not configured")
    r=request("POST",base_url.rstrip("/")+"/chat/completions",headers={"Authorization":f"Bearer {api_key}","Content-Type":"application/json","X-Title":"AI Career Agent"},json={"model":model,"messages":[{"role":"system","content":system},{"role":"user","content":prompt}],"temperature":.35},timeout=self.c.timeout,retries=self.c.retries)
    if not r.ok:raise RuntimeError(f"{provider} HTTP {r.status_code}: {r.text[:800]}")
    x=r.json()["choices"][0]["message"]["content"]
    if isinstance(x,list):x="".join(a.get("text","") for a in x if isinstance(a,dict))
    return str(x).strip()
 def or_chat(self,prompt,system):
    if self.c.aicredits_key:
      return self._chat(prompt,system,self.c.aicredits_base_url,self.c.aicredits_key,self.c.aicredits_chat_model,"AICredits")
    return self._chat(prompt,system,"https://openrouter.ai/api/v1",self.c.openrouter_key,self.c.openrouter_model,"OpenRouter")
 def j(self,prompt,system):
    x=self.or_chat(prompt,system);x=re.sub(r"^```json\s*|\s*```$","",x.strip(),flags=re.I);return json.loads(x)
 def score(self,job,profile):
    try:
      return self.j(json.dumps({"job":job,"profile":profile},ensure_ascii=False),
        "Return JSON only with keys score, reason, matched_skills. Score 0-100 using skill, technology, experience, remote, category, salary, seniority, location, career and portfolio compatibility. Never invent facts; missing data lowers confidence.")
    except Exception:
      # Safe deterministic fallback: only uses explicit source facts and configured profile.
      text=(job.get("title","")+" "+job.get("description","")+" "+" ".join(job.get("skills",[]))).lower()
      wanted=[str(x).lower() for x in profile.get("skills",[])+profile.get("technologies",[])]
      hits=[x for x in wanted if x and x in text]
      role=job.get("title","").lower()
      score=min(89,50+min(30,len(set(hits))*5))
      if any(x in role for x in ["react","next.js","node.js","typescript","python","django","flask","full stack","frontend","backend","web"]):score=min(95,score+10)
      return {"score":score,"reason":"Fallback score based only on explicit job text and configured profile skills; no missing facts were inferred.","matched_skills":hits}
 def post(self,topic):
    return self.j(f"""Topic: {topic}

Return JSON with exactly two keys: caption and image_prompt.
Caption requirements: <=1300 characters; start with a strong but natural hook; explain one useful technical idea in clear human language; use short readable paragraphs; include a practical takeaway; finish with a genuine question or discussion CTA; add 3-6 highly relevant hashtags; never invent personal achievements, client results, statistics, quotes, credentials or news. Avoid generic AI phrases and engagement bait.
Image prompt requirements: create a premium, topic-specific LinkedIn visual for this post. Photorealistic or polished editorial technology photography, strong composition, realistic materials, crisp fine detail, professional lighting, clear focal subject, subtle depth of field, sophisticated corporate-tech aesthetic. Landscape/widescreen composition. Do not render readable text, captions, watermarks, logos, fake UI, generic AI brains, cyberpunk clichés, collages, infographics, excessive blur or distorted objects.
""",
      "You are a precise LinkedIn technology editor. Write useful, credible, human-sounding posts. Never invent personal claims, statistics or credentials.")
