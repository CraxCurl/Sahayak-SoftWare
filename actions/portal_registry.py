"""
Portal Registry - Pre-configured Indian Government and Utility Portals
"""

PORTALS = {
    "mygov": {
        "name": "MyGov India",
        "url": "https://www.mygov.in",
        "keywords": ["mygov", "my gov", "government portal", "gov.in"],
        "description": "Citizen engagement platform of the Government of India"
    },
    "aadhaar": {
        "name": "UIDAI MyAadhaar Portal",
        "url": "https://myaadhaar.uidai.gov.in",
        "keywords": ["aadhaar", "adhar", "uidai", "aadhaar card", "phone update", "mobile update aadhaar", "aadhaar update"],
        "description": "UIDAI portal to check Aadhaar status, update phone number, download e-Aadhaar"
    },
    "voter": {
        "name": "Voters' Services Portal (ECI)",
        "url": "https://voters.eci.gov.in",
        "keywords": ["voter", "voter id", "election commission", "voter card", "epic"],
        "description": "Election Commission of India portal for voter registration and correction"
    },
    "digilocker": {
        "name": "DigiLocker",
        "url": "https://www.digilocker.gov.in",
        "keywords": ["digilocker", "digital locker", "documents", "dl"],
        "description": "Cloud platform for issuance and verification of documents & certificates"
    },
    "pan": {
        "name": "NSDL PAN Card Services",
        "url": "https://www.onlineservices.nsdl.com/paam/endUserRegisterContact.html",
        "keywords": ["pan", "pan card", "nsdl", "apply pan", "pan update"],
        "description": "Apply for new PAN card or request changes/correction in PAN data"
    },
    "passport": {
        "name": "Passport Seva Portal",
        "url": "https://www.passportindia.gov.in",
        "keywords": ["passport", "passport seva", "apply passport"],
        "description": "Official portal for Indian passport application & appointment booking"
    },
    "income_tax": {
        "name": "Income Tax e-Filing Portal",
        "url": "https://www.incometax.gov.in",
        "keywords": ["income tax", "tax", "itr", "efiling"],
        "description": "Income Tax Department e-filing portal"
    },
    "parivahan": {
        "name": "Parivahan Sewa (Vehicle & Driving License)",
        "url": "https://parivahan.gov.in",
        "keywords": ["parivahan", "driving license", "dl", "rc", "challan", "rto"],
        "description": "Ministry of Road Transport and Highways portal for DL and RC services"
    },
    "epfo": {
        "name": "EPFO Member Unified Portal",
        "url": "https://unifiedportal-mem.epfindia.gov.in/memberinterface/",
        "keywords": ["epfo", "pf", "provident fund", "uan", "pf balance"],
        "description": "Employees' Provident Fund Organisation portal for UAN & PF balance"
    },
    "irctc": {
        "name": "IRCTC Train Booking",
        "url": "https://www.irctc.co.in",
        "keywords": ["irctc", "train ticket", "railway", "train reservation"],
        "description": "Indian Railways Catering and Tourism Corporation"
    }
}

def resolve_portal(query: str) -> dict | None:
    """Finds matching portal based on user query keywords."""
    query_lower = query.lower()
    for key, info in PORTALS.items():
        if key in query_lower:
            return info
        for kw in info["keywords"]:
            if kw in query_lower:
                return info
    return None
