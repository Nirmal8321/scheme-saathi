"""Mock data for early UI development - returns sample responses when USE_MOCK=true."""
from typing import Dict, Any, List
from backend.schemas import (
    AnalyzeResponse, Profile, SchemeResult,
    ChatResponse, PdfExplainResponse
)


def get_mock_analyze_response(language: str) -> AnalyzeResponse:
    """Return mock analyze response for the given language."""
    mock_data = {
        "en": {
            "profile": {
                "occupation": "farmer",
                "age": None,
                "gender": None,
                "state": "Maharashtra",
                "district": "Wardha",
                "annual_income": 80000,
                "land_acres": 2.0,
                "caste_category": None,
                "family_members": None
            },
            "missing_fields": ["age", "caste_category"],
            "results": [
                {
                    "scheme_id": "pm_kisan",
                    "scheme": "PM-KISAN",
                    "eligible": "yes",
                    "reason": "Small farmer with land holding.",
                    "benefit": "Rs 6,000 per year in 3 installments",
                    "documents": ["Aadhaar", "7/12 land record", "Bank passbook"],
                    "how_to_apply": "pmkisan.gov.in or nearest CSC center",
                    "official_link": "https://pmkisan.gov.in",
                    "source_quote": "All landholding farmer families are eligible",
                    "explanation": "You get Rs 6,000 every year in three parts. You need Aadhaar, land papers, and bank account. Apply online or at a CSC center."
                },
                {
                    "scheme_id": "namo_shetkari",
                    "scheme": "Namo Shetkari Mahasanman Nidhi",
                    "eligible": "yes",
                    "reason": "Maharashtra farmer with valid land record.",
                    "benefit": "Rs 6,000 per year additional to PM-KISAN",
                    "documents": ["Aadhaar", "7/12 land record", "Bank passbook"],
                    "how_to_apply": "mahadbt.maharashtra.gov.in or nearest CSC",
                    "official_link": "https://mahadbt.maharashtra.gov.in",
                    "source_quote": "Farmers registered under PM-KISAN in Maharashtra",
                    "explanation": "Maharashtra gives you another Rs 6,000 per year on top of PM-KISAN. Same documents needed. Apply on MahaDBT portal."
                },
                {
                    "scheme_id": "mudra_loan",
                    "scheme": "Mudra Loan",
                    "eligible": "maybe",
                    "reason": "Income eligibility needs verification.",
                    "benefit": "Up to Rs 10 lakh loan for business",
                    "documents": ["Aadhaar", "PAN", "Business proof", "Bank statements"],
                    "how_to_apply": "Any bank branch or mudra.org.in",
                    "official_link": "https://mudra.org.in",
                    "source_quote": "Non-corporate, non-farm small/micro enterprises",
                    "explanation": "You may get a loan up to Rs 10 lakh for farming business. Bank will check your income and business plan. Visit any bank."
                }
            ],
            "summary_text": "You qualify for PM-KISAN and Namo Shetkari - Rs 12,000 per year total. Mudra Loan maybe. Need age and caste info for exact check.",
            "language": "en",
            "disclaimer": "Verify at official portal before applying."
        },
        "hi": {
            "profile": {
                "occupation": "किसान",
                "age": None,
                "gender": None,
                "state": "महाराष्ट्र",
                "district": "वर्धा",
                "annual_income": 80000,
                "land_acres": 2.0,
                "caste_category": None,
                "family_members": None
            },
            "missing_fields": ["age", "caste_category"],
            "results": [
                {
                    "scheme_id": "pm_kisan",
                    "scheme": "PM-KISAN",
                    "eligible": "yes",
                    "reason": "छोटे किसान जिनके पास जमीन है।",
                    "benefit": "साल में 6,000 रुपये तीन किश्तों में",
                    "documents": ["आधार", "7/12 जमीन का रिकॉर्ड", "बैंक पासबुक"],
                    "how_to_apply": "pmkisan.gov.in या नजदीकी CSC केंद्र",
                    "official_link": "https://pmkisan.gov.in",
                    "source_quote": "सभी जमीन वाले किसान परिवार पात्र हैं",
                    "explanation": "आपको हर साल 6,000 रुपये तीन हिस्सों में मिलेंगे। आधार, जमीन के कागजात और बैंक खाता चाहिए। ऑनलाइन या CSC सेंटर पर अप्लाई करें।"
                },
                {
                    "scheme_id": "namo_shetkari",
                    "scheme": "नमो शेतकरी महासंमान निधि",
                    "eligible": "yes",
                    "reason": "महाराष्ट्र के किसान जिनके पास वैध जमीन रिकॉर्ड है।",
                    "benefit": "PM-KISAN के अलावा साल में 6,000 रुपये अतिरिक्त",
                    "documents": ["आधार", "7/12 जमीन का रिकॉर्ड", "बैंक पासबुक"],
                    "how_to_apply": "mahadbt.maharashtra.gov.in या नजदीकी CSC",
                    "official_link": "https://mahadbt.maharashtra.gov.in",
                    "source_quote": "महाराष्ट्र में PM-KISAN के तहत पंजीकृत किसान",
                    "explanation": "महाराष्ट्र आपको PM-KISAN के ऊपर और 6,000 रुपये देता है। वही कागजात चाहिए। MahaDBT पोर्टल पर अप्लाई करें।"
                },
                {
                    "scheme_id": "mudra_loan",
                    "scheme": "मुद्रा लोन",
                    "eligible": "maybe",
                    "reason": "आय की पात्रता जांच जरूरी है।",
                    "benefit": "व्यापार के लिए 10 लाख तक का लोन",
                    "documents": ["आधार", "पैन", "व्यापार का सबूत", "बैंक स्टेटमेंट"],
                    "how_to_apply": "कोई भी बैंक शाखा या mudra.org.in",
                    "official_link": "https://mudra.org.in",
                    "source_quote": "गैर-कॉर्पोरेट, गैर-कृषि छोटे/सूक्ष्म उद्यम",
                    "explanation": "आपको खेती के काम के लिए 10 लाख तक का लोन मिल सकता है। बैंक आपकी आय और योजना देखेगा। किसी भी बैंक जाएं।"
                }
            ],
            "summary_text": "आप PM-KISAN और नमो शेतकरी के लिए पात्र हैं - कुल 12,000 रुपये सालाना। मुद्रा लोन शायद। सही जांच के लिए उम्र और जाति की जानकारी चाहिए।",
            "language": "hi",
            "disclaimer": "आवेदन से पहले आधिकारिक पोर्टल पर जांच लें।"
        },
        "mr": {
            "profile": {
                "occupation": "शेतकरी",
                "age": None,
                "gender": None,
                "state": "महाराष्ट्र",
                "district": "वर्धा",
                "annual_income": 80000,
                "land_acres": 2.0,
                "caste_category": None,
                "family_members": None
            },
            "missing_fields": ["age", "caste_category"],
            "results": [
                {
                    "scheme_id": "pm_kisan",
                    "scheme": "PM-KISAN",
                    "eligible": "yes",
                    "reason": "जमीन असलेले लहान शेतकरी।",
                    "benefit": "वर्षात 6,000 रुपये 3 हिशोबात",
                    "documents": ["आधार", "७/१२ जमीन अभिलेख", "बँक पासबुक"],
                    "how_to_apply": "pmkisan.gov.in किंवा जवळची CSC केंद्र",
                    "official_link": "https://pmkisan.gov.in",
                    "source_quote": "सर्व जमीनधारक शेतकरी कुटुंब पात्र आहेत",
                    "explanation": "तुम्हाला दरवर्षी 6,000 रुपये तीन हिशोबात मिळतील। आधार, जमीन कागदपत्रे आणि बँक खाते हवे. ऑनलाइन किंवा CSC केंद्रवर अर्ज करा."
                },
                {
                    "scheme_id": "namo_shetkari",
                    "scheme": "नमो शेतकरी महासंमान निधि",
                    "eligible": "yes",
                    "reason": "महाराष्ट्रातील शेतकरी ज्यांच्याकडे वैध जमीन अभिलेख आहे.",
                    "benefit": "PM-KISAN बरोबरच वर्षात 6,000 रुपये अतिरिक्त",
                    "documents": ["आधार", "७/१२ जमीन अभिलेख", "बँक पासबुक"],
                    "how_to_apply": "mahadbt.maharashtra.gov.in किंवा जवळची CSC",
                    "official_link": "https://mahadbt.maharashtra.gov.in",
                    "source_quote": "महाराष्ट्रात PM-KISAN खाली नोंदणी केलेले शेतकरी",
                    "explanation": "महाराष्ट्र शासन PM-KISAN वरून 6,000 रुपये अधिक देते. तेच कागदपत्रे हवी. MahaDBT पोर्टलवर अर्ज करा."
                },
                {
                    "scheme_id": "mudra_loan",
                    "scheme": "मुद्रा कर्ज",
                    "eligible": "maybe",
                    "reason": "उत्पन्न पात्रता तपासणी आवश्यक आहे.",
                    "benefit": "व्यवसायासाठी 10 लाख पर्यंत कर्ज",
                    "documents": ["आधार", "पॅन", "व्यवसाय पुरावा", "बँक स्टेटमेंट"],
                    "how_to_apply": "कोणताही बँक शाखा किंवा mudra.org.in",
                    "official_link": "https://mudra.org.in",
                    "source_quote": "नॉन-कॉर्पोरेट, नॉन-फार्म लहान/सूक्ष्म उद्योग",
                    "explanation": "शेती व्यवसायासाठी 10 लाख पर्यंत कर्ज मिळू शकतो. बँक तुमचा उत्पन्न आणि योजना तपाशेल. कोणत्याही बँकला जा."
                }
            ],
            "summary_text": "तुम्ही PM-KISAN आणि नमो शेतकरी योजनेसाठी पात्र आहात - एकूण 12,000 रुपये वर्षी. मुद्रा कर्ज शक्य. अचूक तपासणीसाठी वय आणि जातीची माहिती हवी.",
            "language": "mr",
            "disclaimer": "अर्ज करण्यापूर्वी अधिकृत पोर्टलवर तपासा."
        }
    }

    data = mock_data.get(language, mock_data["en"])
    return AnalyzeResponse(**data)


def get_mock_chat_response(question: str, language: str) -> ChatResponse:
    """Return mock chat response for the given question and language."""
    mock_answers = {
        "en": {
            "documents": "For PM-KISAN: Aadhaar, 7/12 land record, Bank passbook. For Namo Shetkari: same documents. For Mudra Loan: Aadhaar, PAN, Business proof, Bank statements.",
            "benefit": "PM-KISAN gives Rs 6,000/year. Namo Shetkari gives another Rs 6,000/year. Total Rs 12,000/year. Mudra Loan up to Rs 10 lakh if eligible.",
            "apply": "PM-KISAN & Namo Shetkari: online at pmkisan.gov.in or mahadbt.maharashtra.gov.in, or visit nearest CSC. Mudra Loan: visit any bank branch.",
            "default": "I can help with documents, benefits, or how to apply for these schemes. What do you need?"
        },
        "hi": {
            "documents": "PM-KISAN के लिए: आधार, 7/12 जमीन रिकॉर्ड, बैंक पासबुक। नमो शेतकरी के लिए: वही कागजात। मुद्रा लोन के लिए: आधार, पैन, व्यापार सबूत, बैंक स्टेटमेंट।",
            "benefit": "PM-KISAN देता है 6,000 रुपये/साल। नमो शेतकरी देता है और 6,000 रुपये/साल। कुल 12,000 रुपये/साल। मुद्रा लोन 10 लाख तक अगर पात्र हुए।",
            "apply": "PM-KISAN और नमो शेतकरी: pmkisan.gov.in या mahadbt.maharashtra.gov.in पर ऑनलाइन, या CSC जाएं। मुद्रा लोन: किसी भी बैंक शाखा जाएं।",
            "default": "मैं इन योजनाओं के कागजात, लाभ, या अप्लाई कैसे करें - इसमें मदद कर सकता हूँ। आपको क्या चाहिए?"
        },
        "mr": {
            "documents": "PM-KISAN साठी: आधार, ७/१२ जमीन अभिलेख, बँक पासबुक. नमो शेतकरी साठी: तेच कागदपत्रे. मुद्रा कर्ज साठी: आधार, पॅन, व्यवसाय पुरावा, बँक स्टेटमेंट.",
            "benefit": "PM-KISAN देते 6,000 रुपये/वर्ष. नमो शेतकरी देते अधिक 6,000 रुपये/वर्ष. एकूण 12,000 रुपये/वर्ष. मुद्रा कर्ज 10 लाख पर्यंत जर पात्र झालास.",
            "apply": "PM-KISAN आणि नमो शेतकरी: pmkisan.gov.in किंवा mahadbt.maharashtra.gov.in वर ऑनलाइन, किंवा जवळची CSC भेट द्या. मुद्रा कर्ज: कोणतीही बँक शाखा भेट द्या.",
            "default": "मी या योजनांचे कागदपत्रे, फायदे, किंवा कसे अर्ज करावे याबाबत मदत करू शकतो. तुम्हाला काय हवं?"
        }
    }

    lang_data = mock_answers.get(language, mock_answers["en"])
    q_lower = question.lower()

    if any(kw in q_lower for kw in ["document", "kagad", "कागद", "दस्तावेज", "कागजात"]):
        answer = lang_data["documents"]
    elif any(kw in q_lower for kw in ["benefit", "fayda", "फायदे", "लाभ", "कितना", "किती"]):
        answer = lang_data["benefit"]
    elif any(kw in q_lower for kw in ["apply", "apply kar", "अर्ज", "कसे", "कैसे", "कहाँ"]):
        answer = lang_data["apply"]
    else:
        answer = lang_data["default"]

    return ChatResponse(answer=answer, sources=["pm_kisan", "namo_shetkari"])


def get_mock_pdf_explain_response(language: str) -> PdfExplainResponse:
    """Return mock PDF explain response for the given language."""
    mock_data = {
        "en": {
            "summary": "This government notification announces new subsidies for small farmers. It increases fertilizer subsidy and adds a new crop insurance benefit.",
            "key_points": [
                "Fertilizer subsidy increased by 20%",
                "New crop insurance for weather damage",
                "Application deadline: March 31, 2026",
                "Only for farmers with less than 5 acres"
            ],
            "who_is_affected": "Small and marginal farmers with landholding under 5 acres",
            "deadlines": ["2026-03-31"],
            "language": "en"
        },
        "hi": {
            "summary": "यह सरकारी अधिसूचना छोटे किसानों के लिए नई सब्सिडी की घोषणा करती है। यह उर्वरक सब्सिडी बढ़ाती है और नई फसल बीमा योजना जोड़ती है।",
            "key_points": [
                "उर्वरक सब्सिडी 20% बढ़ाई गई",
                "मौसम से नुकसान के लिए नई फसल बीमा",
                "आवेदन की अंतिम तारीख: 31 मार्च 2026",
                "केवल 5 एकड़ से कम जमीन वाले किसानों के लिए"
            ],
            "who_is_affected": "5 एकड़ से कम जमीन वाले छोटे और सीमांत किसान",
            "deadlines": ["2026-03-31"],
            "language": "hi"
        },
        "mr": {
            "summary": "हे शासकीय अधिसूचना लहान शेतकऱ्यांसाठी नवीन सब्सिडी घोषित करते. हे खते सब्सिडी वाढवते आणि नवीन पीक विमा योजना जोडते.",
            "key_points": [
                "खते सब्सिडी 20% वाढली",
                "हवामान नुकसानासाठी नवीन पीक विमा",
                "अर्जची शेवटची तारीख: ३१ मार्च २०२६",
                "फक्त ५ एकरपेक्षा कमी जमीन असलेल्या शेतकऱ्यांसाठी"
            ],
            "who_is_affected": "५ एकरपेक्षा कमी जमीन असलेले लहान आणि सीमांत शेतकरी",
            "deadlines": ["2026-03-31"],
            "language": "mr"
        }
    }

    data = mock_data.get(language, mock_data["en"])
    return PdfExplainResponse(**data)