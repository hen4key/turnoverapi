# Importing the FastApi class
from typing import Optional
from fastapi import FastAPI, HTTPException, Cookie, Form
# , Query
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.status import HTTP_403_FORBIDDEN
from starlette.responses import RedirectResponse, Response
from starlette.requests import Request

import re
import urllib3
urllib3.disable_warnings()
import requests
import datetime
# import copy
# import json

from urllib.parse import unquote

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")


def chksum(s):
    cks = 0
    i = 0
    while(i < len(s)):
        cks ^= ord(s[i])
        i += 1
    return cks


def ireplace(old, repl, text):
    return re.sub('(?i)' + (old), lambda m: repl, text)
    # return re.sub('(?i)' + re.escape(old), lambda m: repl, text)


def getUrlFromUsername(j_username):
    domene = "None"
    if j_username is not None:
        j_username = unquote(j_username)
    if ("@" in j_username):
        domene = j_username.split("@")[1]
        u = "https://online3.unitouch.eu:8811"
        if (domene == "rover"):
            u = "https://pro001.unitouch.eu:8811"
            # https://pro001.unitouch.eu:8811/BackOffice/web/saft?company=4&startdate=2019-1-1&enddate=2019-1-31
        if (domene[0] == "b"):
            u = "https://online4.unitouch.eu:8811"
        if (domene[0] == "c"):                      # 8820 for http, 8821 for https
            u = "https://online4.unitouch.eu:8821"
        if (domene[0] == "e"):                      # Hovden  # u = "https://online4.unitouch.eu:15138"
            u = "https://online3.unitouch.eu:8821"
        print(u)
        return u
    return ""


@app.post("/BackOffice/static/auth/j_spring_security_check", tags=["Authenticate"])
async def login(j_username: str = Form(...), j_password: str = Form(...)) -> str:
    #     return await login(j_username, j_password)
    #
    #
    # @app.post("/BackOffice/static/auth/j_spring_security_check", tags=["Authenticate"])
    # async def login(j_username: str = Query(None), j_password: str = Query(None)) -> str:
    """
    # Login
    Authenticate the user with username and password. Gives the user the JSESSIONID cookie
    """
    # jsessionid = None
    session = requests.session()
    """for logging in, returns a cookie"""
    payload = {
        'action': 'j_spring_security_check',
        'j_username': j_username,
        'j_password': j_password,
        'submit': 'Login'
    }
    baseurl = getUrlFromUsername(j_username)
    if not baseurl:
        return "incorrect format on username"
    r = session.post(baseurl + '/BackOffice/static/auth/j_spring_security_check', data=payload, verify=False)
    if r.status_code > 199 and r.status_code < 400:
        # for cookie in session.cookies:
        #    if cookie.name.lower() == "jsessionid":
        #        jsessionid = cookie.value
        session.get(baseurl + "/BackOffice/web/permission", verify=False)
        session.get(baseurl + "/BackOffice/web/company", verify=False)
        # complist = [{sted.get("id"): sted.get("name")} for sted in obj.json().get("Data")]
        # {"Header":{"RecordCount":1,"mainCompany":1,"userDefaultCompanyId":1},"Data":[{"id":1,"nr":1,"name":"Hovden","startdate":"2021-07-05","enddate":"2021-07-05","currency":"NOK"}]}
    else:
        return JSONResponse(status_code=r.status_code, content={"message": "Error"})
        # HTTPException("error", 500)
    # ret = JSONResponse(status_code=r.status_code, content={"JSESSIONID": jsessionid })
    ret = JSONResponse(status_code=r.status_code, content={"message": "Look for JSESSIONID in cookies"})
    # forward cookies
    for cookie in session.cookies:
        ret.set_cookie(key=cookie.name, value=cookie.value, path="/", expires=cookie.expires)
    ret.set_cookie(key="j_username", value=j_username, path="/", expires=cookie.expires)
    return ret
    # JSONResponse(status_code=404, content={"message": "Item not found"})


@app.get("/logout", tags=["Authenticate"])
async def logout_and_remove_cookie(JSESSIONID: str = Cookie(None)):
    """
    # Logout
    This route logs out the user by removing the SESSION cookie from browser.
    No action on server doing this.
    """
    response = RedirectResponse(url="/")
    response.delete_cookie("JSESSIONID")  # domain="localtest.me"
    response.delete_cookie("j_username")
    return response


# /BackOffice/web/company
@app.get("/BackOffice/web/company", tags=["Backoffice"])
async def Backoffice_Web_Company(request: Request, JSESSIONID: str = Cookie(None), j_username: str = Cookie(None)) -> str:
    """
    # Company list
    Returns a list of companies that the authenticated user has access to.
    """
    if JSESSIONID and j_username:
        return await Get_Page_or_readCache(request=request, JSESSIONID=JSESSIONID, j_username=j_username)
    return "Error, no session?"


@app.get("/BackOffice/web/report", tags=["Backoffice"])
async def BackOffice_Web_Report(request: Request, company: int, reportnum: int, startdate: datetime.date = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d"), enddate: datetime.date = None, JSESSIONID: str = Cookie(None), j_username: str = Cookie(None)) -> str:
    """
    # report as json
    reportnum can be:
    * 3 - PLU turnover

    """
    if reportnum != 3:
        ret = JSONResponse(status_code=500, content={"message": "Error: Use reportnum=3 in query"})
        return ret
        # return await JSONResponse(status_code=500, content={"Use reportnum=3 in query"})
    if enddate is None:
        enddate = startdate
    return await Get_Page_or_readCache(request=request, company=company, enddate=enddate, JSESSIONID=JSESSIONID, j_username=j_username)


# @app.get("/report/pluturnover", tags=["Backoffice"])
async def Plu_TurnoverReport(request: Request, company: int, startdate: datetime.date = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d"), enddate: datetime.date = None, JSESSIONID: str = Cookie(None), j_username: str = Cookie(None)) -> str:
    """
    if no enddate is set, it is set to the same as startdate
    """
    if enddate is None:
        enddate = startdate
    return await Get_Page_or_readCache(request=request, overrideurl="/BackOffice/web/report", company=company, enddate=enddate, JSESSIONID=JSESSIONID, j_username=j_username, reportnum=3)


# @app.get("/BackOffice/web/masterdata", tags=["Backoffice"])
async def Backoffice_Web_Masterdata(request: Request, companyId: int = None, masterdataId: int = None, JSESSIONID: str = Cookie(None), page: Optional[int] = None, pageCount: Optional[int] = None, j_username: str = Cookie(None)) -> str:
    """# masterdataId:
    * 1 - employee
    * 2 - department
    * 3 - hour rate
    * 4 + vat (get vatcode)
    * 5 - Rank order form
    * 6 - Rank bill
    * 7 + Financial group
    * 8 - print reports
    * 9 - main group
    * 10 - product
    * 11 - Debtor (kundeliste)
    * 12 - country
    * 13 - Page article
    * 14 - Use lookup
    * 15 - Channel
    * 16 - Channel manager
    * 17 - Pricelist
    * 18 - Currency 1:NOK 6:EURO
    * 19 - Relation
    * 20 - Menu
    * 21 - Tag
    * 22 - weborder - Means of payment weborder
    * 23 - Order type
    * 24 - Delivery area
    * 25 - Pick up address
    * 26 - Opening hours
    * 27 - Order Note
    * 28 + Ledger
    * 29 - Table
    * 30 - Tablemap: 1etg.jpg, 2etg.jpg, ute.jpg
    * 31 - User (Language, Startup)
    * 32 - Rest POS
    * 33 + Payment method
    ### nytt 2021-05-28:
    * 34 - Firma
    * 35 - Admin / Role
    * 40 - Reservering
    * 41    halv dag
    * 42    type
    * 38    Rom
    * 39    Bord view
    * 43    bord skjema
    * 44    bord skjema plan·
    """
    #  : dealer, heytom, staf, salg1, webapp, Norway, English, WebApp, nanopos
    return await Get_Page_or_readCache(request=request, companyId=companyId, JSESSIONID=JSESSIONID, page=page, pageCount=pageCount, j_username=j_username)


async def Get_Page_or_readCache(request: Request, overrideurl: bool = False, companyId: int = None, company: int = None, masterdataId: int = None, JSESSIONID: str = Cookie(None), j_username: str = Cookie(None), page: Optional[int] = None, enddate: Optional[datetime.date] = None, pageCount: Optional[int] = None, reportnum: Optional[int] = None) -> str:
    """for logging in, returns a cookie"""
    if not JSESSIONID or JSESSIONID is None:
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Not authenticated")
    if not j_username or j_username is None:
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Not authenticated")
    print(JSESSIONID)
    cookies_dict = {"JSESSIONID": JSESSIONID}
    q = str(request.query_params)
    print("Q was: %s" % q)
    if enddate is not None:
        q = ireplace('&enddate\\=[0-9\\-]*', "", q)
        q += "&enddate=%s" % enddate
        print("Q new: %s" % q)
    if reportnum is not None:
        q += f"&reportnum={reportnum}"
    urlpath = request.url.path
    if overrideurl:
        urlparts = overrideurl.split('?')
        urlpath = urlparts[0]
        if (len(urlparts) > 1):
            q = urlparts[1]
    print("%s  %s  %s" % (urlpath, request.url.port, request.url.scheme))
    print(q)
    if "&readcache=" in q:
        q = ireplace("&readcache=true", "", q)
        q = ireplace("&readcache=false", "", q)
        q = ireplace("&readcache=None", "", q)
        q = ireplace("&readcache=", "", q)
        print("Removing &readcache....: %s" % q)
    baseurl = getUrlFromUsername(j_username)
    # domain = j_username.split("@")[1]
    print(f"URLPATH {urlpath}")

    r = requests.get(baseurl + urlpath + "?" + q, verify=False, cookies=cookies_dict)
    print(r.text)
    print(r.status_code)
    print(r.headers)
    print(f"Fetched [{r.status_code}]: {baseurl}{urlpath}?{q}")
    if r.status_code > 199 and r.status_code < 400 and "Progress Application Server Error" not in str(r.content) and "Progress Application Server Login" not in str(r.text):
        return r.json()
    return None
    # id = Column(Integer, primary_key=True, index=True)
    # domain = Column(String, index=True)
    # companyid = Column(Integer)
    # reqdata = Column(String)
    # content = Column(LargeBinary)

    # obj.encoding = 'UTF-8'
    # domain = j_username.split("@")[1]
    # db_user = cache_models.Access(j_username=j_username, j_password=j_password, jsessionid=jsessionid, domain=domain, companyids=compids)
    # db.add(db_user)
    # db.commit()
    # db.refresh(db_user)
    # auth: bool = Depends(cookie_auth),
    # session = requests.session()

# https://online3.unitouch.eu:8821/BackOffice/web/masterdata?masterdataId=28&companyId=1&page=1&pageCount=25


# A minimal app to demonstrate the get request
@app.get("/", tags=['root'])
async def root() -> str:
    """Main webpage, nothing special"""
#    return generate_html_response()
    return Response(content="Nothing to see here", media_type="text/html")
