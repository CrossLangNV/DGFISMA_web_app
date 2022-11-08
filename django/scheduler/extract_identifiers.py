import re
from collections import Counter

url_pattern = "(((?!.*\/)[a-z0-9-_]+?)+)"
date_pattern = "([0-9]{1,2}\s[A-Za-z]+\s[0-9]{4})"
patterns = {
    "fsb": date_pattern,
    "bis": date_pattern,
    "srb": date_pattern,
    "esma": "(ESMA[A-Za-z0-9/-]+)",
    "eba": "(EBA[A-Za-z0-9/-]+)",
    "eiopa": "EIOPA[A-Za-z0-9/-]+",
}

CNT = Counter()


def get_source(url):
    source = ""
    for x in patterns.keys():
        if x in url:
            source = x
    return source


def retrieve_identifier(doc):
    url = doc["url"][0]
    source = get_source(url)
    content = doc["content"][0]
    if source not in patterns:
        return ""
    pattern = patterns[source]
    m = re.findall(pattern, content[:250])
    if len(m) == 0:
        m = re.findall(date_pattern, content)
        if len(m) == 0:
            if url[-1] is "/":
                url = url[:-1]
            m = re.findall(url_pattern, url.split("/")[-1].rsplit(".", 1)[0])[0]
        identifier = source.upper() + "_" + m[0].replace(" ", "_").replace("\n", "_").replace(u"\xa0", "_")
    else:
        m = m[0]
        if source in ["fsb", "bis", "srb"]:
            identifier = source.upper() + "_" + m.replace(" ", "_").replace("\n", "_").replace(u"\xa0", "_")
        else:
            identifier = m
            if not any(x.isdigit() for x in m):
                m = re.findall(date_pattern, content)[0]
                identifier = source.upper() + "_" + m.replace(" ", "_").replace("\n", "_").replace(u"\xa0", "_")

    CNT[identifier] += 1
    if CNT[identifier] != 1:
        identifier = identifier + "_" + str(CNT[identifier])
    return identifier
