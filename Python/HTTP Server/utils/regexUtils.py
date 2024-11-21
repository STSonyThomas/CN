from typing import Optional
import re

def regexFunc()->str:
    pattern = r"^[\w.]+@[\w]+\.[\w]+"
    tMatch  = str(input("Enter a string to match: "))
    try:
        match   = re.match(pattern,tMatch)
        print(match.group())
        return match.group()
    except AttributeError:
        print("No match found")
        return ""

def httpRegex(eval:Optional[str]=None)->dict:
    try:
        pattern = r"^\/([a-zA-Z0-9\-.~%]+(\/[a-zA-Z0-9\-.~%]+)*)?(\/?\?([a-zA-Z0-9\-.~%]+=[a-zA-Z0-9\-.~%]+)(&[a-zA-Z0-9\-.~%]+=[a-zA-Z0-9\-.~%]+)*)?$"
        tMatch  =eval if eval else str(input("Enter a string to match: "))
        match = re.match(pattern,tMatch)
        if(not match):
            return{"error":"Invalid String"}
        qPattern = r"[a-zA-Z0-9\-.~%]+=[a-zA-Z0-9\-.~%]+"
        qMatch = re.findall(qPattern,match.group())
        query={}
        for q in qMatch:
            key,value = q.split("=")
            query[key]=value
        print(query)

        return query
    except AttributeError:
        print("No match found")
        return ""

if __name__ == "__main__":
    # regexFunc()
    httpRegex()