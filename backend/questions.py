"""Hardcoded follow-up questions for missing facts, in en, hi, mr."""
from typing import Dict, Optional

# Map of fact key -> {language: question_text}
QUESTION_TEMPLATES: Dict[str, Dict[str, str]] = {
    "bpl_status": {
        "en": "Do you have a BPL ration card?",
        "hi": "क्या आपके पास BPL राशन कार्ड है?",
        "mr": "तुमच्याकडे BPL रेशन कार्ड आहे का?"
    },
    "existing_lpg_connection": {
        "en": "Do you already have an LPG connection in your household?",
        "hi": "क्या आपके घर में पहले से LPG कनेक्शन है?",
        "mr": "तुमच्या घरी आधीच LPG कनेक्शन आहे का?"
    },
    "house_ownership": {
        "en": "Do you own a pucca house anywhere in India?",
        "hi": "क्या भारत में कहीं आपका पक्का मकान है?",
        "mr": "भारतात तुमच्याकडे पक्के घर आहे का?"
    },
    "secc_listing_or_income_proof": {
        "en": "Are you listed in SECC 2011 or do you have income proof?",
        "hi": "क्या आप SECC 2011 में सूचीबद्ध हैं या आपके पास आय प्रमाण है?",
        "mr": "तुमचे नाव SECC 2011 मध्ये आहे का किंवा तुमच्याकडे उत्पन्नाचा पुरावा आहे का?"
    },
    "income_certificate": {
        "en": "Do you have an income certificate?",
        "hi": "क्या आपके पास आय प्रमाण पत्र है?",
        "mr": "तुमच्याकडे उत्पन्न प्रमाणपत्र आहे का?"
    },
    "vending_certificate": {
        "en": "Do you have a Certificate of Vending (CoV) or Identity Card from the ULB?",
        "hi": "क्या आपके पास ULB द्वारा जारी वेंडिंग सर्टिफिकेट (CoV) या पहचान पत्र है?",
        "mr": "तुमच्याकडे ULB द्वारे जारी वेंडिंग सर्टिफिकेट (CoV) किंवा ओळखपत्र आहे का?"
    },
    "caste_category": {
        "en": "What is your caste category (General, SC, ST, OBC, EWS)?",
        "hi": "आपकी जाति श्रेणी क्या है (सामान्य, SC, ST, OBC, EWS)?",
        "mr": "तुमची जात वर्ग काय आहे (सामान्य, SC, ST, OBC, EWS)?"
    },
    "gender": {
        "en": "What is your gender (male/female)?",
        "hi": "आपका लिंग क्या है (पुरुष/महिला)?",
        "mr": "तुमचा लिंग काय आहे (पुरुष/स्त्री)?"
    },
    "age": {
        "en": "What is your age?",
        "hi": "आपकी उम्र क्या है?",
        "mr": "तुमचे वय किती आहे?"
    },
    "occupation": {
        "en": "What is your occupation (farmer, business_owner, street_vendor, student, etc.)?",
        "hi": "आपका व्यवसाय क्या है (किसान, व्यवसायी, स्ट्रीट वेंडर, छात्र, आदि)?",
        "mr": "तुमचा व्यवसाय काय आहे (शेतकरी, व्यवसायी, स्ट्रीट व्हेंडर, विद्यार्थी, इ.)?"
    },
    "annual_income": {
        "en": "What is your annual family income?",
        "hi": "आपकी वार्षिक पारिवारिक आय कितनी है?",
        "mr": "तुमचे वार्षिक कुटुंबीय उत्पन्न किती आहे?"
    },
    "land_acres": {
        "en": "How many acres of cultivable land do you own?",
        "hi": "आपके पास कितने एकड़ खेती योग्य जमीन है?",
        "mr": "तुमच्याकडे किती एकर शेतीयोग्य जमीन आहे?"
    },
}

# Map of verification key -> {language: question_text}
VERIFICATION_QUESTIONS: Dict[str, Dict[str, str]] = {
    "bpl_status": {
        "en": "Do you have a BPL ration card?",
        "hi": "क्या आपके पास BPL राशन कार्ड है?",
        "mr": "तुमच्याकडे BPL रेशन कार्ड आहे का?"
    },
    "existing_lpg_connection": {
        "en": "Do you already have an LPG connection?",
        "hi": "क्या आपके पास पहले से LPG कनेक्शन है?",
        "mr": "तुमच्याकडे आधीच LPG कनेक्शन आहे का?"
    },
    "house_ownership": {
        "en": "Do you own a pucca house?",
        "hi": "क्या आपका पक्का मकान है?",
        "mr": "तुमच्याकडे पक्के घर आहे का?"
    },
    "secc_listing_or_income_proof": {
        "en": "Are you in SECC 2011 list or have income proof?",
        "hi": "क्या आप SECC 2011 सूची में हैं या आय प्रमाण है?",
        "mr": "तुमचे नाव SECC 2011 मध्ये आहे का किंवा उत्पन्नाचा पुरावा आहे का?"
    },
    "family_income_proof": {
        "en": "Do you have a family income certificate?",
        "hi": "क्या आपके पास पारिवारिक आय प्रमाण पत्र है?",
        "mr": "तुमच्याकडे कुटुंबीय उत्पन्न प्रमाणपत्र आहे का?"
    },
    "vending_certificate": {
        "en": "Do you have a vending certificate (CoV) from the ULB?",
        "hi": "क्या आपके पास ULB का वेंडिंग सर्टिफिकेट (CoV) है?",
        "mr": "तुमच्याकडे ULB चे वेंडिंग सर्टिफिकेट (CoV) आहे का?"
    },
    "income_certificate": {
        "en": "Do you have an income certificate?",
        "hi": "क्या आपके पास आय प्रमाण पत्र है?",
        "mr": "तुमच्याकडे उत्पन्न प्रमाणपत्र आहे का?"
    },
}

def get_question(fact_key: str, language: str) -> Optional[str]:
    """Get question text for a missing fact in the specified language."""
    templates = QUESTION_TEMPLATES.get(fact_key)
    if templates:
        return templates.get(language) or templates.get("en")
    # Check verification questions
    v_templates = VERIFICATION_QUESTIONS.get(fact_key)
    if v_templates:
        return v_templates.get(language) or v_templates.get("en")
    return None

def get_verification_question(verification_key: str, language: str) -> Optional[str]:
    """Get question text for a verification key in the specified language."""
    templates = VERIFICATION_QUESTIONS.get(verification_key)
    if templates:
        return templates.get(language) or templates.get("en")
    return None